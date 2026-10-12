import asyncio
import re
from datetime import datetime, timezone

import config
from .task import (
    Task, TaskDeletingError, TaskNotFoundError, TaskPathError, TaskMetadataError, TASK_ID_PATTERN,
)


class TaskManager:
    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self.deleting: set[str] = set()

    def create_task(self, task_id: str, prompt: str) -> dict:
        if task_id in self.deleting:
            raise TaskDeletingError('任务正在删除，请稍后重试')
        task = Task.create(task_id, prompt)
        self.tasks[task_id] = task
        return {'task_id': task_id, 'status': 'created'}

    def _get_task(self, task_id: str) -> Task:
        # 缓存任务实例；历史提示词和事件每次从本任务会话读取。
        Task._task_dir(task_id)
        if task_id not in self.tasks:
            self.tasks[task_id] = Task(task_id)
        return self.tasks[task_id]

    async def delete_task(self, task_id: str) -> dict:
        if task_id in self.deleting:
            raise TaskDeletingError('任务正在删除，请稍后重试')
        task = self._get_task(task_id)
        # 首次校验到标记之间不让出执行权，阻止重复删除和同 ID 重建。
        self.deleting.add(task_id)

        async def remove():
            if task.job is not None:
                if not task.job.done():
                    task.job.cancel()
                # 等待 Agent 上下文退出及元数据 finally，再删除目录。
                await asyncio.gather(task.job, return_exceptions=True)
            await asyncio.to_thread(task.delete_files)
            self.tasks.pop(task_id, None)

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
        jobs = [task.job for task in self.tasks.values()
                if task.job is not None and not task.job.done()]
        for job in jobs:
            job.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)
