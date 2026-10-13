import asyncio
import re
import shutil
from contextlib import nullcontext
import json
import logging
from datetime import datetime, timezone

from . import config
from .task import (
    Task, TaskConflictError, TaskDeletingError, TaskNotFoundError, TaskPathError, TaskMetadataError, TASK_ID_PATTERN, _write_metadata,
)


logger = logging.getLogger(__name__)


class TaskManager:
    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self.deleting: set[str] = set()
        # 所有入口共用一把锁，避免人工任务和项目任务抢占验证资源。
        self.execution_lock = asyncio.Lock()
        self.closing = False
        if config.VIP_TASK_DIR.is_dir():
            for directory in config.VIP_TASK_DIR.iterdir():
                try:
                    directory = Task._task_dir(directory.name)
                    metadata = Task._metadata(directory)
                    if metadata['status'] in ('created', 'queued', 'running'):
                        metadata['status'] = 'cancelled'
                        metadata['chatstatus'] = 'cancelled'
                        _write_metadata(directory / 'task.json', metadata)
                        logger.warning('服务重启，取消未完成任务 task_id=%s', directory.name)
                except (TaskPathError, TaskNotFoundError, TaskMetadataError, OSError, ValueError, KeyError):
                    continue

    def create_task(self, task_id: str, prompt: str, *, start: bool = True) -> dict:
        if task_id in self.deleting:
            raise TaskDeletingError('任务正在删除，请稍后重试')
        task = Task.create(task_id, prompt, start=False)
        self.tasks[task_id] = task
        if start:
            self._schedule(task)
        return {'task_id': task_id, 'status': 'queued' if start else 'created'}

    def _schedule(self, task: Task):
        metadata_path = task.task_dir / 'task.json'
        metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
        task.turn_id += 1
        if not task.chat_mode and not task.events:
            task.write_event({'type': 'user', 'message': task.prompt})
        metadata['turn_id'] = task.turn_id
        metadata['status'] = 'queued'
        metadata['chatstatus'] = 'queued'
        _write_metadata(metadata_path, metadata)
        task.job = asyncio.create_task(self._execute(task))
        logger.info('任务进入队列 task_id=%s', task.task_id)

    async def _execute(self, task: Task):
        try:
            async with self.execution_lock:
                if task.chat_mode:
                    if task.pending:
                        messages = task.pending[:]
                        task.pending.clear()
                        task.inflight = messages
                        await task.async_run('\n\n'.join(messages))
                else:
                    await task.run()
                # settled 与发送竞争时，未送入旧进程的消息在同一资源锁内续跑。
                while task.pending and not task.pausing:
                    task.chat_mode = True
                    messages = task.pending[:]
                    task.pending.clear()
                    task.inflight = messages
                    task.turn_id += 1
                    await task.async_run('\n\n'.join(messages))
        except asyncio.CancelledError:
            # 等待锁时也需结束任务状态。
            metadata_path = task.task_dir / 'task.json'
            metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
            metadata['status'] = 'paused' if task.pausing else 'cancelled'
            metadata['chatstatus'] = metadata['status']
            _write_metadata(metadata_path, metadata)
            logger.info('任务已取消 task_id=%s', task.task_id)
            if not task.pausing:
                raise
        finally:
            if task.inflight:
                task.pending[:0] = task.inflight
                task.inflight = []

    async def send_message(self, task_id: str, message: str):
        if task_id in self.deleting:
            raise TaskDeletingError('任务正在删除')
        task = self._get_task(task_id)
        async with task.control_lock:
            if self.closing or task.pausing or task_id in self.deleting:
                raise TaskConflictError('任务正在停止或删除')
            if not isinstance(message, str) or not message.strip():
                raise TaskPathError('message 不能为空', 400)
            status = Task._metadata(task.task_dir)['status']
            if status == 'created' or (task.preparation and not task.preparation.done()):
                raise TaskConflictError('任务尚在准备输入')
            if not task.events:
                for event in task.read_history().events:
                    task.write_event(event)
            agent = task.agent
            if task.job is not None and not task.job.done():
                task.pending.append(message)
                task.write_event({'type': 'user', 'message': message})
                if agent is not None and not agent.settled:
                    try:
                        result = await agent.rpc('prompt', message=message, streamingBehavior='followUp')
                        if result.get('disposition') == 'handled' and message in task.pending:
                            task.pending.remove(message)
                    except (RuntimeError, OSError, TimeoutError):
                        # 保留消息，让旧进程退出后重试，不丢上下文。
                        return {'task_id': task_id, 'status': 'queued'}
                    return {'task_id': task_id, 'status': 'running'}
                return {'task_id': task_id, 'status': 'queued'}
            task.chat_mode = task.chat_mode or bool(task.read_history().prompt) or not task.events
            if task.chat_mode:
                # 老任务尚无独立验证状态，在聊天改写 status 前保留原结论。
                metadata_path = task.task_dir / 'task.json'
                metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
                metadata.setdefault('verification_status', status)
                _write_metadata(metadata_path, metadata)
            task.pending.append(message)
            self._schedule(task)
            task.write_event({'type': 'user', 'message': message})
            return {'task_id': task_id, 'status': 'queued'}

    async def pause_task(self, task_id: str):
        if task_id in self.deleting:
            raise TaskDeletingError('任务正在删除')
        task = self._get_task(task_id)
        async with task.control_lock:
            if task_id in self.deleting or self.closing:
                raise TaskConflictError('任务正在删除或关闭')
            if Task._metadata(task.task_dir)['status'] == 'created':
                raise TaskConflictError('任务尚在准备输入')
            task.pausing = True
            try:
                if task.job is not None and not task.job.done():
                    task.job.cancel()
                    operation = asyncio.ensure_future(asyncio.gather(task.job, return_exceptions=True))
                    try:
                        await asyncio.shield(operation)
                    except asyncio.CancelledError:
                        await operation
                        task.set_status('paused')
                        raise
                task.set_status('paused')
                task.write_event({'type': 'status', 'status': 'paused'})
            finally:
                task.pausing = False
            return {'task_id': task_id, 'status': 'paused'}

    async def prepare_task(self, task_id: str, collect, *args):
        if task_id in self.deleting:
            raise TaskDeletingError('任务正在删除')
        task = self._get_task(task_id)
        task.preparation = asyncio.create_task(asyncio.to_thread(collect, *args))
        try:
            return await asyncio.shield(task.preparation)
        except asyncio.CancelledError:
            # 文件线程无法强制取消，退出前等待其结束。
            await asyncio.gather(task.preparation, return_exceptions=True)
            raise

    async def run_task(self, task_id: str):
        if task_id in self.deleting:
            raise TaskDeletingError('任务正在删除')
        task = self._get_task(task_id)
        if task.job is None:
            if Task._metadata(task.task_dir)['status'] != 'created':
                raise ValueError('只有新建任务可以启动')
            self._schedule(task)
        await task.job

    def _get_task(self, task_id: str) -> Task:
        # 缓存任务实例；历史提示词和事件每次从本任务会话读取。
        Task._task_dir(task_id)
        if task_id not in self.tasks:
            self.tasks[task_id] = Task(task_id)
        return self.tasks[task_id]

    async def delete_task(self, task_id: str) -> dict:
        if task_id in self.deleting:
            raise TaskDeletingError('任务正在删除，请稍后重试')
        Task._task_dir(task_id)
        # 历史任务删除不加载对话，损坏的记录不能阻止永久清理。
        task = self.tasks.get(task_id)
        # 首次校验到标记之间不让出执行权，阻止重复删除和同 ID 重建。
        self.deleting.add(task_id)

        async def remove():
            async with (task.control_lock if task is not None else nullcontext()):
                await remove_locked()

        async def remove_locked():
            # 输入收集也属于任务生命周期，避免复制与 rmtree 同时操作目录。
            if task is not None:
                if task.preparation is not None:
                    await asyncio.gather(task.preparation, return_exceptions=True)
                if task.job is not None:
                    if not task.job.done():
                        task.job.cancel()
                    # 等待 Agent 上下文退出及元数据 finally，再删除目录。
                    await asyncio.gather(task.job, return_exceptions=True)
            await asyncio.to_thread(shutil.rmtree, Task._task_dir(task_id))
            self.tasks.pop(task_id, None)
            logger.info('任务已删除 task_id=%s', task_id)

        operation = asyncio.create_task(remove())
        try:
            try:
                await asyncio.shield(operation)
            except asyncio.CancelledError:
                # 请求断开也要等清理完成，不能提前解除重建保护。
                await operation
                raise
            return {'task_id': task_id, 'status': 'deleted'}
        finally:
            self.deleting.discard(task_id)

    def list_tasks(self) -> dict:
        root = config.VIP_TASK_DIR
        if not root.is_dir():
            return {'tasks': []}
        tasks = []
        # 仅枚举任务根目录的直接子目录，忽略不可读或无效任务。
        for entry in root.iterdir():
            if not re.fullmatch(TASK_ID_PATTERN, entry.name) or len(entry.name) > 64:
                continue
            try:
                task = Task._metadata(Task._task_dir(entry.name))
                task['prompt'] = self._get_task(entry.name).get_prompt()
                tasks.append(task)
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
        return self._get_task(task_id).get_task()

    def get_file(self, task_id: str, path: str):
        return self._get_task(task_id).get_file(path)

    def get_events(self, task_id: str):
        return self._get_task(task_id).get_events()

    async def close(self):
        self.closing = True
        preparations = [task.preparation for task in self.tasks.values()
                        if task.preparation is not None and not task.preparation.done()]
        await asyncio.gather(*preparations, return_exceptions=True)
        for task in list(self.tasks.values()):
            async with task.control_lock:
                if task.job is not None and not task.job.done():
                    task.job.cancel()
                    await asyncio.gather(task.job, return_exceptions=True)
        # 协程尚未开始时取消，不会进入 finally，仍需落盘终态。
        for task in self.tasks.values():
            try:
                path = task.task_dir / 'task.json'
                metadata = json.loads(path.read_text(encoding='utf-8'))
                if metadata['status'] in ('created', 'queued', 'running'):
                    metadata['status'] = 'cancelled'
                    metadata['chatstatus'] = 'cancelled'
                    _write_metadata(path, metadata)
            except FileNotFoundError:
                continue
