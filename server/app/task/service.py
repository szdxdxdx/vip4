import asyncio
import json
from contextlib import aclosing
from datetime import datetime, timezone
from pathlib import Path

from .. import config
from ..agent.stream import agent_events


class TaskExistsError(Exception):
    pass


class TaskNotFoundError(Exception):
    pass


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
        (task_dir / 'task.json').write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8',
        )
        (task_dir / '.gitignore').write_text('*\n', encoding='utf-8')
        (task_dir / 'events.jsonl').touch()

        agent_prompt = f'/skill:verify-ip 工作目录为 {workspace}\n\n{prompt}'
        job = asyncio.create_task(self._run(task_dir, agent_prompt))
        self.jobs[task_id] = job
        job.add_done_callback(lambda _: self.jobs.pop(task_id, None))
        return {'task_id': task_id, 'status': 'created'}

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
        metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
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
                metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')

    async def close(self):
        jobs = list(self.jobs.values())
        for job in jobs:
            job.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)
