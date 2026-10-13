"""项目映射持久化及后台编排，不持久化项目运行状态。"""
import asyncio
import logging
import json
import os
import secrets
import string
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from . import config
from .file_sources import FileSources
from .task import Task, TaskExistsError, TaskNotFoundError, _write_metadata

logger = logging.getLogger(__name__)
TERMINAL = {'completed', 'failed', 'cancelled', 'deleted'}


class ProjectConflictError(Exception):
    pass


class ProjectNotFoundError(Exception):
    pass


class ProjectStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute('CREATE TABLE IF NOT EXISTS project_tasks '
                        "(task_id TEXT PRIMARY KEY, projectID TEXT NOT NULL, ip_id TEXT NOT NULL DEFAULT '')")
        # 已有映射自动补列，保留历史任务及归属。
        columns = {row[1] for row in self.db.execute('PRAGMA table_info(project_tasks)')}
        if 'ip_id' not in columns:
            self.db.execute("ALTER TABLE project_tasks ADD COLUMN ip_id TEXT NOT NULL DEFAULT ''")
        self.db.execute('CREATE INDEX IF NOT EXISTS project_id ON project_tasks(projectID)')
        self.db.commit()

    def tasks(self, project_id: str) -> list[str]:
        return [row[0] for row in self.db.execute(
            'SELECT task_id FROM project_tasks WHERE projectID=? ORDER BY rowid', (project_id,))]

    def entries(self, project_id: str) -> list[dict]:
        return [{'task_id': task_id, 'ip_id': ip_id} for task_id, ip_id in self.db.execute(
            'SELECT task_id, ip_id FROM project_tasks WHERE projectID=? ORDER BY rowid', (project_id,))]

    def add(self, task_id: str, project_id: str, ip_id: str):
        with self.db:
            self.db.execute('INSERT INTO project_tasks (task_id, projectID, ip_id) VALUES (?, ?, ?)',
                            (task_id, project_id, ip_id))

    def remove(self, project_id: str):
        with self.db:
            self.db.execute('DELETE FROM project_tasks WHERE projectID=?', (project_id,))

    def has_task(self, task_id: str) -> bool:
        return self.db.execute('SELECT 1 FROM project_tasks WHERE task_id=?', (task_id,)).fetchone() is not None

    def close(self):
        self.db.close()


class ProjectManager:
    def __init__(self, task_manager, store: ProjectStore | None = None,
                 sources: FileSources | None = None):
        self.task_manager = task_manager
        self.sources = sources or FileSources()
        self.store = store or ProjectStore(Path(os.getenv(
            'VIP_PROJECT_DB', str(config.VIP_TASK_DIR.parent / 'projects.sqlite3'))))
        self.projects: dict[str, dict] = {}
        self.jobs: dict[str, asyncio.Task] = {}
        self.closed = False
        self.resets: dict[str, asyncio.Task] = {}

    async def submit(self, project_id: str, prompt: str | None = None, *, force: bool = False):
        if self.closed:
            raise ProjectConflictError('服务正在关闭')
        if project_id in self.resets:
            raise ProjectConflictError('项目正在强制重建，请稍后重试')
        exists = project_id in self.projects or self.store.tasks(project_id)
        if exists and not force:
            raise ProjectConflictError('项目已提交；可选择强制提交删除旧任务并重新验证')
        if not force:
            return self._start(project_id, prompt)
        operation = asyncio.create_task(self._replace(project_id, prompt))
        self.resets[project_id] = operation
        def finished(job):
            # 并发保护由清理操作释放，不受 HTTP 请求重复取消影响。
            if self.resets.get(project_id) is job:
                self.resets.pop(project_id, None)
            if not job.cancelled():
                job.exception()
        operation.add_done_callback(finished)
        return await asyncio.shield(operation)

    def _start(self, project_id: str, prompt: str | None):
        if self.closed:
            raise ProjectConflictError('服务正在关闭')
        self.projects[project_id] = {'status': 'accepted'}
        self.jobs[project_id] = asyncio.create_task(self._run(project_id, prompt))
        logger.info('项目已接受 projectID=%s', project_id)
        return {'projectID': project_id, 'status': 'accepted'}

    async def _replace(self, project_id: str, prompt: str | None):
        self.projects[project_id] = {'status': 'resetting'}
        logger.info('开始强制重建 projectID=%s', project_id)
        try:
            job = self.jobs.get(project_id)
            if job is not None:
                if not job.done():
                    job.cancel()
                await asyncio.gather(job, return_exceptions=True)
            # 旧编排的 finally 可能写 cancelled，保持重建状态直至删除完成。
            self.projects[project_id] = {'status': 'resetting'}
            for task_id in self.store.tasks(project_id):
                try:
                    await self.task_manager.delete_task(task_id)
                except TaskNotFoundError:
                    pass
            # 文件全部删除成功后才移除映射；失败时保留归属供查询及重试。
            self.store.remove(project_id)
            self.jobs.pop(project_id, None)
            logger.info('旧项目任务已清理 projectID=%s', project_id)
            return self._start(project_id, prompt)
        except Exception as error:
            self.projects[project_id] = {'status': 'failed', 'error': f'强制重建失败：{error}', 'requires_resubmit': True}
            logger.exception('强制重建失败 projectID=%s', project_id)
            raise

    async def _blocking(self, call, *args):
        # 取消时等待文件收集结束，避免关闭后仍有线程修改任务输入。
        job = asyncio.create_task(asyncio.to_thread(call, *args))
        try:
            return await asyncio.shield(job)
        except asyncio.CancelledError:
            await asyncio.gather(job, return_exceptions=True)
            raise

    def _create(self, project_id: str, prompt: str | None, ip_id: str) -> str:
        for _ in range(1000):
            task_id = datetime.now().strftime('%m%d') + ''.join(
                secrets.choice(string.ascii_lowercase + string.digits) for _ in range(4))
            if self.store.has_task(task_id):
                continue
            directory = (config.VIP_TASK_DIR / task_id).resolve()
            instructions = (
                f'使用 verify-ip SKILL，使用 CBMC 对此软件 IP 进行完整形式化验证。\n'
                f'只读输入目录：{directory / "input"}\n'
                f'输入来源清单：{directory / "files.csv"}\n'
                f'报告按 SKILL 约定写入 {directory / "workspace"}/<tool>_suite/output'
                f'（CBMC 使用 cbmc_suite/output），驱动、配置和工具输出遵循 SKILL 目录约定；'
                f'临时文件写入 workspace/tmp。'
            )
            if prompt:
                instructions += f'\n用户要求：{prompt}'
            try:
                self.task_manager.create_task(task_id, instructions, start=False)
            except TaskExistsError:
                continue
            try:
                self.store.add(task_id, project_id, ip_id)
            except Exception:
                self._mark_unfinished(task_id)
                raise
            return task_id
        raise RuntimeError('无法分配任务 ID：碰撞重试次数超限')

    def _mark_unfinished(self, task_id: str, status: str = 'cancelled'):
        # 尚未执行的任务也必须落盘为 cancelled，不能留下假运行状态。
        path = config.VIP_TASK_DIR / task_id / 'task.json'
        if not path.exists():
            return
        try:
            metadata = json.loads(path.read_text(encoding='utf-8'))
            if metadata['status'] in ('created', 'queued', 'running'):
                metadata['status'] = status
                _write_metadata(path, metadata)
        except (OSError, ValueError, KeyError):
            logger.exception('无法更新任务状态 task_id=%s status=%s', task_id, status)

    async def _run(self, project_id: str, prompt: str | None):
        state = self.projects[project_id]
        try:
            state['status'] = 'collecting'
            items = await self._blocking(self.sources.search, project_id)
            if not items:
                state['status'] = 'empty'
                return
            # 每条 IP 独立准备；全部准备结束后才启动成功准备的任务。
            errors = []
            pairs = []
            for item in items:
                try:
                    # 只保存实体模型的业务标识，不记录 name 或数据库数字 ipId。
                    value = item
                    for key in ('ipMsg', 'entity', 'basicInformation', 'id'):
                        value = value.get(key) if isinstance(value, dict) else None
                    ip_id = value.strip() if isinstance(value, str) else ''
                    pairs.append((self._create(project_id, prompt, ip_id), item))
                except Exception as error:
                    state['requires_resubmit'] = True
                    errors.append(f'IP {item["ipId"]} 创建失败：{error}')
                    logger.exception('IP 创建失败 projectID=%s ipId=%s', project_id, item['ipId'])
            ready = []
            for task_id, item in pairs:
                try:
                    await self.task_manager.prepare_task(task_id, self.sources.collect, item,
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
            state.update(status='failed', error=str(error))
            logger.exception('项目执行失败 projectID=%s', project_id)
        finally:
            for task_id in self.store.tasks(project_id):
                self._mark_unfinished(task_id)
            logger.info('项目状态 projectID=%s status=%s', project_id, state['status'])

    def _task(self, task_id: str) -> dict:
        try:
            task = Task._metadata(Task._task_dir(task_id))
            # 普通聊天状态不能覆盖项目的验证结论。
            if 'verification_status' in task:
                task['chatstatus'] = task.get('chatstatus', task['status'])
                task['status'] = task['verification_status']
            return task
        except TaskNotFoundError:
            return {'task_id': task_id, 'status': 'deleted'}

    def progress(self, project_id: str) -> dict:
        entries = self.store.entries(project_id)
        state = {'status': 'resetting'} if project_id in self.resets else self.projects.get(project_id)
        if not entries and state is None:
            raise ProjectNotFoundError('项目不存在')
        tasks = [{**self._task(entry['task_id']), 'ip_id': entry['ip_id']} for entry in entries]
        if tasks and state is not None and not state.get('requires_resubmit') and state['status'] in ('completed', 'failed', 'cancelled'):
            if all(task['status'] == 'completed' for task in tasks):
                state = {'status': 'completed'}
        if state is None:
            statuses = [task['status'] for task in tasks]
            status = ('completed' if all(s == 'completed' for s in statuses) else
                      'cancelled' if any(s in ('created', 'queued', 'running', 'cancelled') for s in statuses)
                      else 'failed')
            state = {'status': status}
        state = {key: value for key, value in state.items() if key != 'requires_resubmit'}
        return {'projectID': project_id, **state, 'total': len(tasks),
                'finished': sum(t['status'] in TERMINAL for t in tasks), 'tasks': tasks}

    def results(self, project_id: str) -> dict:
        progress = self.progress(project_id)
        tasks = []
        for task in progress['tasks']:
            files = []
            if task['status'] != 'deleted':
                for file in self.task_manager.get_task(task['task_id'])['files']:
                    if 'output' not in Path(file['path']).parts[:-1]:
                        continue
                    files.append({**file, 'download_url': '/task/get_file?' + urlencode({
                        'task_id': task['task_id'], 'path': file['path'], 'download': 'true'})})
            tasks.append({'task_id': task['task_id'], 'ip_id': task['ip_id'],
                          'status': task['status'], 'files': files})
        return {'projectID': project_id, 'tasks': tasks}

    async def close(self):
        self.closed = True
        # 等待已接受的永久清理；_start 会拒绝关闭期间启动新项目。
        await asyncio.gather(*list(self.resets.values()), return_exceptions=True)
        for job in self.jobs.values():
            if not job.done():
                job.cancel()
        await asyncio.gather(*self.jobs.values(), return_exceptions=True)
        self.store.close()
