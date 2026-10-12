import asyncio
import re
from datetime import datetime, timezone

import config
from .task import (
    Task, TaskNotFoundError, TaskPathError, TaskMetadataError, TASK_ID_PATTERN,
)


class TaskManager:
    def __init__(self):
        self.tasks: dict[str, Task] = {}

    def create_task(self, task_id: str, prompt: str) -> dict:
        task = Task.create(task_id, prompt)
        self.tasks[task_id] = task
        return {'task_id': task_id, 'status': 'created'}

    def _get_task(self, task_id: str) -> Task:
        # 缓存任务实例；历史提示词和事件每次从本任务会话读取。
        if task_id not in self.tasks:
            self.tasks[task_id] = Task(task_id)
        return self.tasks[task_id]

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
