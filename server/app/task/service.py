import asyncio
import json
import mimetypes
import os
import re
import tempfile
from dataclasses import dataclass
from contextlib import aclosing
from datetime import datetime, timezone
from pathlib import Path

from .. import config
from ..agent.stream import agent_events


class TaskExistsError(Exception):
    pass


class TaskNotFoundError(Exception):
    pass


class TaskPathError(Exception):
    """Malformed path (400) or disallowed filesystem access (403)."""

    def __init__(self, message: str, status_code: int = 403):
        super().__init__(message)
        self.status_code = status_code


class TaskMetadataError(Exception):
    pass


class TaskReadLimitError(Exception):
    pass


@dataclass(frozen=True)
class WorkspaceFile:
    path: Path
    kind: str
    media_type: str
    attachment: bool = False


TASK_ID_PATTERN = r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$'
MAX_SCAN_ENTRIES = 20000
MAX_WORKSPACE_FILES = 5000


def _write_metadata(path: Path, metadata: dict):
    # Readers see either the old or new complete document, never partial JSON.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', dir=path.parent,
            prefix='.task-', suffix='.tmp', delete=False,
        ) as output:
            temporary = Path(output.name)
            output.write(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class TaskManager:
    def __init__(self):
        self.jobs: dict[str, asyncio.Task] = {}

    def create_task(self, task_id: str, prompt: str) -> dict:
        config.VIP_TASK_DIR.mkdir(parents=True, exist_ok=True)
        task_dir = config.VIP_TASK_DIR / task_id
        try:
            task_dir.mkdir()
        except FileExistsError:
            raise TaskExistsError('task_id 已存在，请使用新的任务 ID') from None

        session_dir = task_dir / 'session'
        workspace = task_dir / 'workspace'
        for directory in (session_dir, workspace):
            directory.mkdir()

        metadata = {
            'task_id': task_id,
            'prompt': prompt,
            'status': 'created',
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        _write_metadata(task_dir / 'task.json', metadata)
        (task_dir / '.gitignore').write_text('*\n', encoding='utf-8')
        (task_dir / 'events.jsonl').touch()

        agent_prompt = f'/skill:verify-ip 工作目录为 {workspace}\n\n{prompt}'
        job = asyncio.create_task(self._run(task_dir, agent_prompt))
        self.jobs[task_id] = job
        job.add_done_callback(lambda _: self.jobs.pop(task_id, None))
        return {'task_id': task_id, 'status': 'created'}

    @staticmethod
    def _task_dir(task_id: str) -> Path:
        if len(task_id) > 64 or not re.fullmatch(TASK_ID_PATTERN, task_id):
            raise TaskPathError('非法 task_id', 400)
        root = config.VIP_TASK_DIR.resolve()
        directory = root / task_id
        if directory.is_symlink():
            raise TaskPathError('不允许任务目录符号链接')
        if not directory.is_dir():
            raise TaskNotFoundError('任务不存在')
        if directory.resolve().parent != root:
            raise TaskPathError('任务目录越界')
        return directory

    @staticmethod
    def _workspace(task_dir: Path) -> Path:
        workspace = task_dir / 'workspace'
        if workspace.is_symlink():
            raise TaskPathError('不允许 workspace 符号链接')
        if not workspace.is_dir():
            raise TaskNotFoundError('workspace 不存在')
        if workspace.resolve().parent != task_dir:
            raise TaskPathError('workspace 越界')
        return workspace

    @staticmethod
    def _relative_path(value: str) -> Path:
        # Also reject Windows-style paths, although the backend runs on Linux.
        if not value or '\\' in value or ':' in value or '\x00' in value:
            raise TaskPathError('非法文件路径', 400)
        parts = value.split('/')
        if any(part in ('', '.', '..') for part in parts):
            raise TaskPathError('必须使用 workspace 相对路径', 400)
        if any(part.startswith('.') or part in ('tmp', '__pycache__') for part in parts):
            raise TaskPathError('不允许访问隐藏或临时文件')
        return Path(*parts)

    @classmethod
    def _workspace_file(cls, workspace: Path, value: str) -> WorkspaceFile:
        relative = cls._relative_path(value)
        path = workspace
        for part in relative.parts:
            path = path / part
            if path.is_symlink():
                raise TaskPathError('不允许文件或目录符号链接')
        try:
            resolved = path.resolve(strict=True)
        except (FileNotFoundError, NotADirectoryError):
            raise TaskNotFoundError('文件不存在') from None
        if not resolved.is_relative_to(workspace) or not resolved.is_file():
            if not resolved.is_relative_to(workspace):
                raise TaskPathError('文件路径越界')
            raise TaskNotFoundError('文件不存在')
        kind = {'report.html': 'report_html', 'report.json': 'report_json'}.get(path.name, 'file')
        # Never serve arbitrary active content as executable same-origin content.
        media_type = 'text/plain'
        attachment = False
        if kind == 'report_html':
            media_type = 'text/html'
        elif path.suffix.lower() == '.json':
            media_type = 'application/json'
        elif path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
            media_type = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                          '.gif': 'image/gif', '.webp': 'image/webp'}[path.suffix.lower()]
        else:
            guessed_type, _ = mimetypes.guess_type(path.name)
            if guessed_type and not (
                guessed_type.startswith('text/') or
                guessed_type in ('application/javascript', 'application/xml',
                                 'application/xhtml+xml', 'image/svg+xml')
            ):
                # Known binary formats retain their MIME type, but are downloads.
                media_type = guessed_type
                attachment = True
        return WorkspaceFile(resolved, kind, media_type, attachment)

    @classmethod
    def _metadata(cls, task_dir: Path) -> dict:
        source = task_dir / 'task.json'
        if source.is_symlink():
            raise TaskPathError('不允许元数据符号链接')
        try:
            metadata = json.loads(source.read_text(encoding='utf-8'))
        except FileNotFoundError:
            raise TaskNotFoundError('任务元数据不存在') from None
        except (ValueError, UnicodeError):
            raise TaskMetadataError('任务元数据损坏') from None
        if not isinstance(metadata, dict) or any(
            not isinstance(metadata.get(key), str)
            for key in ('prompt', 'status', 'created_at')
        ):
            raise TaskMetadataError('任务元数据格式错误')
        task = {'task_id': task_dir.name, **{
            key: metadata[key] for key in ('prompt', 'status', 'created_at')
        }}
        if isinstance(metadata.get('reports'), list):
            reports = []
            for report in metadata['reports']:
                if not isinstance(report, str):
                    continue
                try:
                    cls._workspace_file(cls._workspace(task_dir), report)
                except (TaskPathError, TaskNotFoundError, OSError):
                    continue
                reports.append(report)
            task['reports'] = reports
        return task

    def list_tasks(self) -> dict:
        root = config.VIP_TASK_DIR
        if not root.is_dir():
            return {'tasks': []}
        tasks = []
        # Only immediate task directories; never search outside the tasks root.
        for entry in root.iterdir():
            if not re.fullmatch(TASK_ID_PATTERN, entry.name) or len(entry.name) > 64:
                continue
            try:
                tasks.append(self._metadata(self._task_dir(entry.name)))
            except (TaskNotFoundError, TaskPathError, TaskMetadataError, OSError):
                continue
        def created_order(task):
            try:
                created = datetime.fromisoformat(task['created_at'])
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                return created.timestamp(), task['task_id']
            except (ValueError, OverflowError):
                return float('-inf'), task['task_id']

        tasks.sort(key=created_order, reverse=True)
        return {'tasks': tasks}

    def get_task(self, task_id: str) -> dict:
        task_dir = self._task_dir(task_id)
        task = self._metadata(task_dir)
        workspace = self._workspace(task_dir)
        files = []
        pending = [workspace]
        scanned = 0
        while pending:
            directory = pending.pop()
            # Recheck queued directories: do not follow a replaced symlink.
            if directory.is_symlink() or not directory.resolve().is_relative_to(workspace):
                continue
            try:
                with os.scandir(directory) as entries:
                    for entry in entries:
                        scanned += 1
                        if scanned > MAX_SCAN_ENTRIES:
                            raise TaskReadLimitError('workspace 文件数量超过扫描上限')
                        if entry.name.startswith('.') or entry.name in ('tmp', '__pycache__'):
                            continue
                        if entry.is_symlink():
                            continue
                        path = Path(entry.path)
                        try:
                            if entry.is_dir(follow_symlinks=False):
                                pending.append(path)
                            elif entry.is_file(follow_symlinks=False):
                                relative = path.relative_to(workspace).as_posix()
                                file = self._workspace_file(workspace, relative)
                                files.append({'path': relative, 'size': file.path.stat().st_size,
                                              'kind': file.kind})
                                if len(files) > MAX_WORKSPACE_FILES:
                                    raise TaskReadLimitError('workspace 文件数量超过返回上限')
                        except (FileNotFoundError, TaskNotFoundError, TaskPathError):
                            continue
            except FileNotFoundError:
                continue
        files.sort(key=lambda file: (file['kind'] == 'file', file['path']))
        return {'task': task, 'files': files}

    def get_file(self, task_id: str, path: str) -> WorkspaceFile:
        return self._workspace_file(self._workspace(self._task_dir(task_id)), path)

    def get_events(self, task_id: str):
        output = config.VIP_TASK_DIR / task_id / 'events.jsonl'
        if not output.is_file():
            raise TaskNotFoundError('任务不存在')

        async def stream():
            with output.open(encoding='utf-8') as file:
                while True:
                    line = file.readline()
                    if line:
                        yield line
                    elif task_id not in self.jobs:
                        return
                    else:
                        await asyncio.sleep(0.05)

        return stream()

    async def _run(self, task_dir: Path, prompt: str):
        metadata_file = task_dir / 'task.json'
        metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
        metadata['status'] = 'running'
        _write_metadata(metadata_file, metadata)
        status = 'completed'
        with (task_dir / 'events.jsonl').open('a', encoding='utf-8') as output:
            def write(event):
                output.write(json.dumps(event, ensure_ascii=False) + '\n')
                output.flush()

            try:
                async with aclosing(agent_events(
                    prompt, cwd=task_dir / 'workspace', session_dir=task_dir / 'session',
                )) as events:
                    async for event in events:
                        write({'type': 'agent', 'data': event})
                        if event.get('type') == 'error':
                            status = 'failed'
                if status == 'completed':
                    reports = []
                    workspace = task_dir / 'workspace'
                    for report in workspace.glob('*_suite/output/report.json'):
                        html = report.with_suffix('.html')
                        if html.is_file() and html.stat().st_size:
                            json.loads(report.read_text(encoding='utf-8'))
                            reports.append(str(report.relative_to(workspace)))
                    if not reports:
                        status = 'failed'
                        write({'type': 'error', 'error': 'Agent 已停止，但未生成最终验证报告，任务未完成'})
                    metadata['reports'] = reports
            except asyncio.CancelledError:
                status = 'cancelled'
                write({'type': 'error', 'error': '服务关闭，任务已取消'})
                raise
            except Exception:
                status = 'failed'
                write({'type': 'error', 'error': '任务执行失败'})
            finally:
                metadata['status'] = status
                _write_metadata(metadata_file, metadata)

    async def close(self):
        jobs = list(self.jobs.values())
        for job in jobs:
            job.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)
