import asyncio
import json
import mimetypes
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from contextlib import aclosing
from datetime import datetime, timezone
from pathlib import Path

from . import config
from ..agent import config as agent_config
from ..agent.pi import PiAgent
from .pi_session import read_history


class TaskExistsError(Exception):
    pass


class TaskNotFoundError(Exception):
    pass


class TaskDeletingError(Exception):
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


def _write_metadata(path: Path, metadata: dict):
    # 原子替换元数据，避免订阅读到未写完的 JSON。
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


class Task:
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.task_dir = config.VIP_TASK_DIR / task_id
        self.events: list[str] = []
        self.prompt: str = ''
        self.job: asyncio.Task | None = None

    @classmethod
    def create(cls, task_id: str, prompt: str):
        # 初始化单任务目录与元数据，执行不依赖事件订阅。
        config.VIP_TASK_DIR.mkdir(parents=True, exist_ok=True)
        task_dir = config.VIP_TASK_DIR / task_id
        try:
            task_dir.mkdir()
        except FileExistsError:
            raise TaskExistsError('task_id 已存在，请使用新的任务 ID') from None

        session_dir = task_dir / 'pi_session'
        workspace = task_dir / 'workspace'
        for directory in (session_dir, workspace):
            directory.mkdir()

        metadata = {
            'task_id': task_id,
            'status': 'created',
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        _write_metadata(task_dir / 'task.json', metadata)
        (task_dir / '.gitignore').write_text('*\n', encoding='utf-8')

        agent_prompt = f'/skill:verify-ip 工作目录为 {workspace}\n\n{prompt}'
        task = cls(task_id)
        task.prompt = prompt
        task.job = asyncio.create_task(task.async_run(agent_prompt))
        return task

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

    def delete_files(self):
        # 仅删除经校验的任务根目录；rmtree 不跟随内部符号链接。
        shutil.rmtree(self._task_dir(self.task_id))

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
        # 同时拒绝 Windows 路径，统一限定为 workspace 相对路径。
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
        # 报告之外的主动内容按纯文本提供，避免同源执行。
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
                # 二进制保留 MIME 类型，但只能下载。
                media_type = guessed_type
                attachment = True
        return WorkspaceFile(resolved, kind, media_type, attachment)

    @classmethod
    def _metadata(cls, task_dir: Path) -> dict:
        # 校验元数据，并仅返回仍可安全读取的报告路径。
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
            for key in ('status', 'created_at')
        ):
            raise TaskMetadataError('任务元数据格式错误')
        task = {'task_id': task_dir.name, **{
            key: metadata[key] for key in ('status', 'created_at')
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

    def get_task(self) -> dict:
        task_dir = self._task_dir(self.task_id)
        task = self._metadata(task_dir)
        task['prompt'] = self.get_prompt()
        workspace = self._workspace(task_dir)
        # 有界扫描工作区，保留原文件分类与返回顺序。
        files = []
        pending = [workspace]
        scanned = 0
        while pending:
            directory = pending.pop()
            # 扫描时重新检查目录边界，跳过隐藏、临时文件和符号链接。
            if directory.is_symlink() or not directory.resolve().is_relative_to(workspace):
                continue
            try:
                with os.scandir(directory) as entries:
                    for entry in entries:
                        scanned += 1
                        if scanned > config.MAX_SCAN_ENTRIES:
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
                                if len(files) > config.MAX_WORKSPACE_FILES:
                                    raise TaskReadLimitError('workspace 文件数量超过返回上限')
                        except (FileNotFoundError, TaskNotFoundError, TaskPathError):
                            continue
            except FileNotFoundError:
                continue
        files.sort(key=lambda file: (file['kind'] == 'file', file['path']))
        return {'task': task, 'files': files}

    def get_file(self, path: str) -> WorkspaceFile:
        return self._workspace_file(self._workspace(self._task_dir(self.task_id)), path)

    def read_history(self):
        return read_history(self._task_dir(self.task_id),
                            config.VIP_SKILL_DIR / 'verify-ip' / 'SKILL.md')

    def get_prompt(self) -> str:
        if self.job is not None and not self.job.done():
            return self.prompt
        return self.read_history().prompt

    def get_events(self):
        self._task_dir(self.task_id)
        live = self.job is not None and not self.job.done()

        async def stream():
            # 订阅开始时固定来源，运行结束后只排空内存，不拼接历史。
            if not live:
                for event in self.read_history().events:
                    yield json.dumps(event, ensure_ascii=False) + '\n'
                return
            index = 0
            while True:
                if index < len(self.events):
                    line = self.events[index]
                    index += 1
                    yield line
                elif self.job is None or self.job.done():
                    return
                else:
                    await asyncio.sleep(config.EVENT_POLL_INTERVAL)

        return stream()

    def _create_agent(self) -> PiAgent:
        # 验证任务运行边界，并集中配置验证专用参数、提示词和临时环境。
        cwd = (self.task_dir / 'workspace').expanduser().resolve(strict=True)
        if (
            cwd.name != 'workspace'
            or cwd.parent.parent != config.VIP_TASK_DIR.resolve()
            or not cwd.is_dir()
        ):
            raise ValueError('Agent 工作目录必须是 tasks/<task_id>/workspace/')
        session_dir = (cwd.parent / 'pi_session').resolve()
        session_dir.mkdir(parents=True, exist_ok=True)
        tmp_dir = cwd / 'tmp'
        tmp_dir.mkdir(exist_ok=True)

        if not config.VIP_SKILL_DIR.is_dir():
            raise FileNotFoundError(f'Skill 目录不存在：{config.VIP_SKILL_DIR}')

        return PiAgent(
            argv=[
                agent_config.PI_EXECUTABLE,
                '--mode', 'rpc',
                '--tools', config.PI_TOOLS,
                '--no-extensions',
                '--no-approve',
                '--no-skills',
                '--skill', str(config.VIP_SKILL_DIR),
                '--no-prompt-templates',
                '--no-context-files',
                '--append-system-prompt', (
                    f'本轮软件 IP 验证工作目录只能是 {cwd}。'
                    f'所有输出和临时文件写入该目录，临时文件放在 {tmp_dir}。'
                    f'输入数据 {config.VIP_DATASET_DIR} 只读；'
                    f'允许读取 {config.VIP_SKILL_DIR} 中的 SKILL、参考文档，执行其脚本与已准备的虚拟环境。'
                    '不得读写其他任务或未指定的数据目录，不得修改原始 IP、SKILL 或全局环境。'
                    '按用户指定 SKILL 执行完整流程，不限制工具调用次数。'
                    '只有最终验证报告生成后才算任务完成，不得捏造工具结果。'
                    '完成任务后最终回复必须且只能是【任务已完成】，不得附带摘要、报告路径或其他文字。'
                    '若未完成或遇到无法继续的问题，必须如实说明，禁止回复【任务已完成】。'
                ),
            ],
            cwd=cwd,
            session_dir=session_dir,
            env={
                **os.environ,
                'TMPDIR': str(tmp_dir), 'TMP': str(tmp_dir), 'TEMP': str(tmp_dir),
                'PYTHONDONTWRITEBYTECODE': '1',
            },
        )

    async def _agent_events(self, prompt: str):
        # 按原完成信号等待回复，并把调用异常转成既有事件文本。
        try:
            async with self._create_agent() as agent, asyncio.timeout(config.PI_TIMEOUT):
                await asyncio.to_thread(agent.send_prompt, prompt)
                message = {}
                while True:
                    event = await asyncio.to_thread(agent.receive)
                    if event.get("type") == "response" and event.get("command") == "prompt":
                        if not event.get("success") or event.get("data", {}).get("disposition") == "handled":
                            raise RuntimeError("Pi 未接受对话请求")
                    elif event.get("type") == "message_end":
                        if event["message"].get("role") == "assistant":
                            message = event["message"]
                    elif event.get("type") == "agent_settled":
                        if event.get("aborted") or message.get("stopReason") not in ("stop", "length"):
                            raise RuntimeError("Pi 未能生成回复")
                    yield event
                    if event.get("type") == "agent_settled":
                        return
        except TimeoutError:
            yield {"type": "error", "error": "LLM 回复超时"}
        except (OSError, RuntimeError, ValueError):
            yield {"type": "error", "error": "Pi 调用失败，请检查模型配置"}

    async def async_run(self, prompt: str):
        # 后台执行、内存事件与报告完成门槛属于单任务生命周期。
        task_dir = self.task_dir
        metadata_file = task_dir / 'task.json'
        metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
        metadata['status'] = 'running'
        _write_metadata(metadata_file, metadata)
        status = 'completed'
        def write(event):
            self.events.append(json.dumps(event, ensure_ascii=False) + '\n')

        try:
            async with aclosing(self._agent_events(prompt)) as events:
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

