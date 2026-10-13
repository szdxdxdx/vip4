"""验证队列测试，不启动真实 Pi。"""
import asyncio
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from app.vip_task.task import Task
from app.vip_task.task_manager import TaskManager

class QueueTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.config = patch('app.vip_task.config.VIP_TASK_DIR', self.root)
        self.config.start()
        self.manager = TaskManager()

    async def asyncTearDown(self):
        await self.manager.close()
        self.config.stop()
        self.directory.cleanup()

    async def test_manual_and_project_share_serial_queue(self):
        active = 0
        peak = 0
        order = []
        async def fake_run(task):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            order.append(task.task_id)
            await asyncio.sleep(.01)
            active -= 1
        with patch.object(Task, 'run', fake_run):
            self.manager.create_task('manual', '本机任务')
            self.manager.create_task('project1', '项目任务', start=False)
            self.manager.create_task('project2', '项目任务', start=False)
            self.assertIsNone(self.manager.tasks['project1'].job)
            await self.manager.run_task('project1')
            await self.manager.run_task('project2')
        self.assertEqual(peak, 1)
        self.assertEqual(order, ['manual', 'project1', 'project2'])

    async def test_delete_waiting_task_does_not_start_pi(self):
        entered = asyncio.Event()
        release = asyncio.Event()
        started = []
        async def fake_run(task):
            started.append(task.task_id)
            entered.set()
            await release.wait()
        with patch.object(Task, 'run', fake_run):
            self.manager.create_task('first', '任务')
            await entered.wait()
            self.manager.create_task('waiting', '任务')
            await asyncio.sleep(0)
            await self.manager.delete_task('waiting')
            release.set()
            await self.manager.tasks['first'].job
        self.assertEqual(started, ['first'])
        self.assertFalse((self.root / 'waiting').exists())

    async def test_restart_marks_unfinished_task_cancelled(self):
        self.manager.create_task('prepared', '任务', start=False)
        self.assertTrue((self.root / 'prepared' / 'input').is_dir())
        TaskManager()
        metadata = json.loads((self.root / 'prepared' / 'task.json').read_text())
        self.assertEqual(metadata['status'], 'cancelled')

    async def test_task_completion_requires_reports(self):
        async def events(task, prompt):
            yield {'type': 'agent_settled'}
        with patch.object(Task, '_agent_events', events):
            self.manager.create_task('no_report', '任务', start=False)
            await self.manager.run_task('no_report')
        self.assertEqual(self.manager.get_task('no_report')['task']['status'], 'failed')

    async def test_completion_and_shutdown_queued_metadata(self):
        async def events(task, prompt):
            output = task.task_dir / 'workspace' / 'cbmc_suite' / 'output'
            output.mkdir(parents=True)
            (output / 'report.json').write_text('{}')
            (output / 'report.html').write_text('<html>报告</html>')
            yield {'type': 'agent_settled'}
        with patch.object(Task, '_agent_events', events):
            self.manager.create_task('reports', '任务', start=False)
            await self.manager.run_task('reports')
        self.assertEqual(self.manager.get_task('reports')['task']['status'], 'completed')
        self.manager.create_task('shutdown', '任务')
        await self.manager.close()
        self.assertEqual(self.manager.get_task('shutdown')['task']['status'], 'cancelled')

    async def test_corrupt_metadata_is_skipped_during_restart(self):
        directory = self.root / 'corrupt'
        directory.mkdir()
        (directory / 'task.json').write_text('[]')
        TaskManager()
        self.assertEqual((directory / 'task.json').read_text(), '[]')

    async def test_list_nonempty_tasks_and_ignore_invalid_directory(self):
        self.manager.create_task('manual', '保留原提示词', start=False)
        (self.root / '.invalid').mkdir()
        tasks = self.manager.list_tasks()['tasks']
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['task_id'], 'manual')
        self.assertEqual(tasks[0]['prompt'], '保留原提示词')

    async def test_delete_waits_for_collection_before_removing_directory(self):
        self.manager.create_task('collecting', '任务', start=False)
        entered = threading.Event()
        release = threading.Event()
        directory = self.root / 'collecting'
        def collect():
            entered.set()
            if not release.wait(5):
                raise TimeoutError('测试未释放收集线程')
            (directory / 'input' / 'code.c').write_text('C')
        preparation = asyncio.create_task(self.manager.prepare_task('collecting', collect))
        await asyncio.to_thread(entered.wait, 5)
        removal = asyncio.create_task(self.manager.delete_task('collecting'))
        try:
            await asyncio.sleep(.01)
            self.assertFalse(removal.done())
            self.assertTrue(directory.exists())
            self.assertIn('collecting', self.manager.deleting)
        finally:
            release.set()
            await preparation
            await removal
        self.assertFalse(directory.exists())
