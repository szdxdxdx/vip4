"""项目映射持久化及后台编排，不持久化项目运行状态。"""
import asyncio
import logging
import json
import os
import sqlite3
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode

from . import config
from .timestamp import HISTORICAL_TIMESTAMP, new_timestamp
from .keti2_sources import Keti2Sources
from .keti3_sources import Keti3Sources
from .task import Task, TaskNotFoundError, TaskPathError, TaskMetadataError, _write_metadata

logger = logging.getLogger(__name__)
TERMINAL = {'completed', 'failed', 'cancelled', 'deleted', 'missing'}
ProjectKey = tuple[str, str, str]


class ProjectConflictError(Exception):
    pass


class ProjectNotFoundError(Exception):
    pass


class ProjectStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        # 重建旧表以解除 projectID 非空约束，历史来源保持 NULL。
        with self.db:
            self.db.execute("CREATE TABLE IF NOT EXISTS project_tasks (task_id TEXT PRIMARY KEY, projectID TEXT, ip_id TEXT NOT NULL DEFAULT '', keti TEXT, timestamp TEXT)")
            columns = {row[1]: row for row in self.db.execute('PRAGMA table_info(project_tasks)')}
            if 'keti' not in columns or 'ip_id' not in columns or columns['projectID'][3]:
                self.db.execute("CREATE TABLE project_tasks_new (task_id TEXT PRIMARY KEY, projectID TEXT, ip_id TEXT NOT NULL DEFAULT '', keti TEXT, timestamp TEXT)")
                ip = 'ip_id' if 'ip_id' in columns else "''"
                keti = 'keti' if 'keti' in columns else 'NULL'
                timestamp = 'timestamp' if 'timestamp' in columns else repr(HISTORICAL_TIMESTAMP)
                self.db.execute(f'INSERT INTO project_tasks_new SELECT task_id, projectID, {ip}, {keti}, {timestamp} FROM project_tasks')
                self.db.execute('DROP TABLE project_tasks')
                self.db.execute('ALTER TABLE project_tasks_new RENAME TO project_tasks')
            elif 'timestamp' not in columns:
                self.db.execute('ALTER TABLE project_tasks ADD COLUMN timestamp TEXT')
                self.db.execute('UPDATE project_tasks SET timestamp=?', (HISTORICAL_TIMESTAMP,))
            self.db.execute('CREATE INDEX IF NOT EXISTS project_id ON project_tasks(keti, projectID)')

    def tasks(self, project_id: str, keti: str | None = None) -> list[str]:
        return [entry['task_id'] for entry in self.entries(project_id, keti)]

    def entries(self, project_id: str, keti: str | None = None) -> list[dict]:
        return [{'task_id': task_id, 'ip_id': ip_id, 'timestamp': timestamp} for task_id, ip_id, timestamp in self.db.execute(
            'SELECT task_id, ip_id, timestamp FROM project_tasks WHERE projectID=? AND keti IS ? ORDER BY rowid', (project_id, keti))]

    def all_entries(self) -> list[dict]:
        return [dict(zip(('task_id', 'projectID', 'ip_id', 'keti', 'timestamp'), row)) for row in self.db.execute(
            'SELECT task_id, projectID, ip_id, keti, timestamp FROM project_tasks ORDER BY rowid DESC')]

    def add(self, task_id: str, project_id: str | None, ip_id: str, keti: str | None = None,
            timestamp: str | None = None):
        with self.db:
            self.db.execute('INSERT INTO project_tasks (task_id, projectID, ip_id, keti, timestamp) VALUES (?, ?, ?, ?, ?)',
                            (task_id, project_id, ip_id, keti, timestamp or new_timestamp()))

    def remove_task(self, task_id: str):
        with self.db:
            self.db.execute('DELETE FROM project_tasks WHERE task_id=?', (task_id,))

    def has_task(self, task_id: str) -> bool:
        return self.db.execute('SELECT 1 FROM project_tasks WHERE task_id=?', (task_id,)).fetchone() is not None

    def close(self):
        self.db.close()


class ProjectManager:
    def __init__(self, task_manager, store: ProjectStore | None = None,
                 keti2_sources: Keti2Sources | None = None, keti3_sources: Keti3Sources | None = None):
        self.task_manager = task_manager
        self.keti2_sources = keti2_sources or Keti2Sources()
        self.keti3_sources = keti3_sources or Keti3Sources()
        self.store = store or ProjectStore(Path(os.getenv(
            'VIP_PROJECT_DB', str(config.VIP_TASK_DIR.parent / 'projects.sqlite3'))))
        self.task_manager.store = self.store
        self.projects: dict[ProjectKey, dict] = {}
        self.jobs: dict[ProjectKey, asyncio.Task] = {}
        # 映射写入及回滚同时失败时保留归属，供本进程查询及按任务删除。
        self.unmapped: dict[ProjectKey, list[dict]] = {}
        self.closed = False
        self._close_job: asyncio.Task | None = None

    async def submit(self, project_id: str, prompt: str | None = None, *,
                     source: Literal['keti2', 'keti3'] = 'keti2', tool: str = 'CBMC'):
        from .inputs import TOOLS
        if tool not in TOOLS:
            raise ValueError('不支持的验证工具')
        if self.closed:
            raise ProjectConflictError('服务正在关闭')
        if source == 'keti3':
            self.keti3_sources.validate(project_id)
        return self._start((source, project_id, new_timestamp()), prompt, tool)

    def _start(self, key: ProjectKey, prompt: str | None, tool: str):
        if self.closed:
            raise ProjectConflictError('服务正在关闭')
        self.projects[key] = {'status': 'accepted', 'source': key[0]}
        self.jobs[key] = asyncio.create_task(self._run(key, prompt, tool))
        logger.info('项目已接受 projectID=%s', key)
        return {'projectID': key[1], 'keti': key[0], 'timestamp': key[2], 'status': 'accepted'}

    async def _blocking(self, call, *args):
        # 取消时等待文件收集结束，避免关闭后仍有线程修改任务输入。
        job = asyncio.create_task(asyncio.to_thread(call, *args))
        try:
            return await asyncio.shield(job)
        except asyncio.CancelledError:
            await asyncio.gather(job, return_exceptions=True)
            raise

    def _create(self, key: ProjectKey, prompt: str | None, ip_id: str, ip_name: str = '', tool: str = 'CBMC') -> str:
        from .inputs import create_registered, CreationRollbackError
        try:
            task_id = create_registered(self.task_manager, self.store, ip_name, tool, prompt,
                                        project_id=key[1], keti=key[0], ip_id=ip_id, timestamp=key[2])['task_id']
            self.task_manager.set_preparation(task_id, 'downloading')
            return task_id
        except CreationRollbackError as error:
            self.unmapped.setdefault(key, []).append({'task_id': error.task_id, 'ip_id': ip_id, 'timestamp': key[2]})
            self._mark_unfinished(error.task_id)
            raise

    def _mark_unfinished(self, task_id: str, status: str = 'cancelled'):
        # 原验证结束后可能已开始续聊；活跃 job 的状态由任务自身维护。
        task = self.task_manager.tasks.get(task_id)
        if task is not None and task.job is not None and not task.job.done():
            return
        # 尚未执行的任务也必须落盘为 cancelled，不能留下假运行状态。
        path = config.VIP_TASK_DIR / task_id / 'task.json'
        if not path.exists():
            return
        try:
            metadata = json.loads(path.read_text(encoding='utf-8'))
            if metadata['status'] in ('created', 'queued', 'running'):
                metadata['status'] = status
                metadata['chatstatus'] = status
                # 初始化验证结论或结束未完成验证，不覆盖已完成验证后的聊天结论。
                if metadata.get('verification_status', 'created') in ('created', 'queued', 'running'):
                    metadata['verification_status'] = status
                _write_metadata(path, metadata)
        except (OSError, ValueError, KeyError):
            logger.exception('无法更新任务状态 task_id=%s status=%s', task_id, status)

    async def _run(self, key: ProjectKey, prompt: str | None, tool: str):
        state = self.projects[key]
        sources = self.keti3_sources if key[0] == 'keti3' else self.keti2_sources
        try:
            state['status'] = 'collecting'
            items = await self._blocking(sources.search, key[1])
            if not items:
                state['status'] = 'empty'
                return
            # 每条 IP 独立准备；全部准备结束后才启动成功准备的任务。
            errors = []
            pairs = []
            for item in items:
                try:
                    # 数据库只保存业务标识，名称写入任务元数据。
                    basic = item
                    for field in ('ipMsg', 'entity', 'basicInformation'):
                        basic = basic.get(field) if isinstance(basic, dict) else None
                    basic = basic if isinstance(basic, dict) else {}
                    ip_id = basic.get('id')
                    ip_id = ip_id.strip() if isinstance(ip_id, str) else ''
                    name = basic.get('name')
                    name = name.strip() if isinstance(name, str) else ''
                    pairs.append((self._create(key, prompt, ip_id, name, tool), item))
                except Exception as error:
                    state['requires_resubmit'] = True
                    errors.append(f'IP {item["ipId"]} 创建失败：{error}')
                    logger.exception('IP 创建失败 projectID=%s ipId=%s', key, item['ipId'])
            ready = []
            for task_id, item in pairs:
                try:
                    await self.task_manager.prepare_task(task_id, sources.collect, item,
                                                         config.VIP_TASK_DIR / task_id)
                    ready.append(task_id)
                except Exception as error:
                    self._mark_unfinished(task_id, 'failed')
                    errors.append(f'任务 {task_id} 输入准备失败：{error}')
                    logger.exception('输入准备失败 task_id=%s', task_id)
            state['status'] = 'running'
            for task_id in ready:
                try:
                    await self.task_manager.run_task(task_id)
                except asyncio.CancelledError:
                    # 单任务删除取消子 job，不应取消整个项目或剩余任务。
                    if asyncio.current_task().cancelling():
                        raise
                    errors.append(f'任务 {task_id} 已取消或删除')
                except Exception as error:
                    self._mark_unfinished(task_id, 'failed')
                    errors.append(f'任务 {task_id} 执行失败：{error}')
                    logger.exception('任务执行失败 task_id=%s', task_id)
            statuses = [self._task(task_id)['status'] for task_id, _ in pairs]
            state['status'] = 'completed' if not errors and all(s == 'completed' for s in statuses) else 'failed'
            if state['status'] == 'failed':
                state['error'] = '; '.join(errors) or '部分任务未完成，请查看任务状态'
        except asyncio.CancelledError:
            state.update(status='cancelled', error='项目编排已取消')
            raise
        except Exception as error:
            state.update(status='failed', error=f'项目输入查询或打包失败：{error}')
            logger.exception('项目执行失败 projectID=%s', key)
        finally:
            for entry in self._entries(key):
                self._mark_unfinished(entry['task_id'])
            logger.info('项目状态 projectID=%s status=%s', key, state['status'])

    def _task(self, task_id: str) -> dict:
        try:
            task = Task._metadata(Task._task_dir(task_id))
            # 普通聊天状态不能覆盖项目的验证结论。
            if 'verification_status' in task:
                task['chatstatus'] = task.get('chatstatus', task['status'])
                task['status'] = task['verification_status']
            return task
        except (TaskNotFoundError, TaskPathError, TaskMetadataError, OSError):
            missing = not (config.VIP_TASK_DIR / task_id).is_dir()
            return {'task_id': task_id, 'ip_name': '', 'status': 'missing',
                    'directory_missing': missing, 'data_missing': not missing}

    def _entries(self, key: ProjectKey) -> list[dict]:
        entries = [entry for entry in self.store.entries(key[1], key[0]) if entry['timestamp'] == key[2]]
        mapped = {entry['task_id'] for entry in entries}
        return entries + [entry for entry in self.unmapped.get(key, [])
                          if entry['task_id'] not in mapped and
                          (entry['task_id'] in self.task_manager.tasks or
                           (config.VIP_TASK_DIR / entry['task_id']).exists())]

    def _batch_progress(self, key: ProjectKey) -> dict:
        entries = self._entries(key)
        state = self.projects.get(key)
        tasks = [{**self._task(entry['task_id']), 'ip_id': entry['ip_id'], 'timestamp': key[2]}
                 for entry in entries]
        if tasks and state is not None and not state.get('requires_resubmit') and state['status'] in ('completed', 'failed', 'cancelled'):
            if all(task['status'] == 'completed' for task in tasks):
                state = {**state, 'status': 'completed'}
                state.pop('error', None)
        if state is None:
            statuses = [task['status'] for task in tasks]
            status = ('completed' if all(s == 'completed' for s in statuses) else
                      'cancelled' if any(s in ('created', 'queued', 'running', 'cancelled') for s in statuses)
                      else 'failed')
            state = {'status': status}
        state = {name: value for name, value in state.items() if name not in ('requires_resubmit', 'source')}
        return {'timestamp': key[2], **state, 'total': len(tasks),
                'finished': sum(t['status'] in TERMINAL for t in tasks), 'tasks': tasks}

    def progress(self, project_id: str, *, source: str) -> dict:
        timestamps = {entry['timestamp'] for entry in self.store.entries(project_id, source)}
        timestamps.update(key[2] for key in self.projects if key[:2] == (source, project_id))
        if not timestamps:
            raise ProjectNotFoundError('项目不存在')
        batches = [self._batch_progress((source, project_id, timestamp)) for timestamp in sorted(timestamps, key=lambda value: value or '')]
        tasks = [task for batch in batches for task in batch['tasks']]
        # 顶层状态采用最新提交批次；任务与计数包含全部批次。
        return {'projectID': project_id, 'keti': source, 'status': batches[-1]['status'], 'source': source,
                **({'error': batches[-1]['error']} if 'error' in batches[-1] else {}),
                'total': len(tasks), 'finished': sum(t['status'] in TERMINAL for t in tasks),
                'tasks': tasks, 'batches': batches}

    def results(self, project_id: str, *, source: str) -> dict:
        progress = self.progress(project_id, source=source)
        tasks = []
        for task in progress['tasks']:
            files = []
            if task['status'] not in ('deleted', 'missing'):
                for file in self.task_manager.get_task(task['task_id'])['files']:
                    if 'output' not in Path(file['path']).parts[:-1]:
                        continue
                    files.append({**file, 'download_url': '/task/get_file?' + urlencode({
                        'task_id': task['task_id'], 'path': file['path'], 'download': 'true'})})
            tasks.append({'task_id': task['task_id'], 'ip_id': task['ip_id'],
                          'timestamp': task['timestamp'], 'status': task['status'], 'files': files})
        return {'projectID': project_id, 'keti': source, 'tasks': tasks,
                'batches': [{'timestamp': batch['timestamp'],
                             'tasks': [task for task in tasks if task['timestamp'] == batch['timestamp']]}
                            for batch in progress['batches']]}

    async def close(self):
        self.closed = True
        if self._close_job is None:
            self._close_job = asyncio.create_task(self._close())
            self._close_job.add_done_callback(lambda job: None if job.cancelled() else job.exception())
        # 关闭调用被取消也不能提前关闭 SQLite。
        await asyncio.shield(self._close_job)

    async def _close(self):
        for job in self.jobs.values():
            if not job.done():
                job.cancel()
        await asyncio.gather(*self.jobs.values(), return_exceptions=True)
        self.store.close()
