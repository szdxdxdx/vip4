"""隔离任务目录和数据库，以伪后端验证课题五交互。"""
import asyncio
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import uvicorn
import httpx
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.service.api import router
from app.service.project_api import ProjectRequest
from app.vip_task import config, keti5
from app.vip_task.inputs import create_registered, create_local
from app.vip_task.project import ProjectManager, ProjectStore
from app.vip_task.task import Task, _write_metadata
from app.vip_task.task_manager import TaskManager
from tmp_keti5.tmp_keti5 import app, records

PARAMS = dict(projectId='123', jobName='流水线', buildId='922337203685477580812345',
              toolName='工具', executionId='9e174276-fb22-4625-bb0f-17e4ea971415')


class Keti5Tests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        sock = socket.socket()
        sock.bind(('127.0.0.1', 0))
        cls.port = sock.getsockname()[1]
        cls.server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
        cls.thread = threading.Thread(target=cls.server.run, kwargs={'sockets': [sock]}, daemon=True)
        cls.thread.start()
        for _ in range(200):
            if cls.server.started:
                break
            time.sleep(.01)
        assert cls.server.started

    @classmethod
    def tearDownClass(cls):
        cls.server.should_exit = True
        cls.thread.join(5)

    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.path_patch = patch.object(config, 'VIP_TASK_DIR', self.root / 'tasks')
        self.path_patch.start()
        base = f'http://127.0.0.1:{self.port}'
        self.settings = patch.multiple(config, KETI5_UPLOAD_URL=base + '/sw/idep/plugin/reportUpload',
                                       KETI5_CALLBACK_URL=base + '/demo-callback/notify')
        self.settings.start()
        self.store = ProjectStore(self.root / 'projects.sqlite3')
        self.manager = TaskManager()
        self.manager.store = self.store
        self.manager.keti5 = keti5.Keti5(self.store)
        records.clear()

    async def asyncTearDown(self):
        await self.manager.close()
        self.store.close()
        self.settings.stop()
        self.path_patch.stop()
        self.tmp.cleanup()

    def create(self, params=PARAMS, timestamp='batch'):
        result = create_registered(self.manager, self.store, '测试', 'CBMC', None,
                                   project_id='123', keti='keti2', timestamp=timestamp, keti5=params)
        return self.manager.tasks[result['task_id']]

    def status(self, task, status):
        path = task.task_dir / 'task.json'
        metadata = json.loads(path.read_text())
        metadata.update(status=status, verification_status=status)
        _write_metadata(path, metadata)

    async def test_parameters(self):
        self.assertIsNone(keti5.parameters({'projectId': '123'}))
        self.assertIsNone(ProjectRequest(projectID='123', keti5={'projectId': '123'}).keti5)
        self.assertEqual(ProjectRequest(projectID='123', keti5=PARAMS).keti5, PARAMS)
        with self.assertRaises(ValueError):
            ProjectRequest(projectID='999', keti5=PARAMS)
        local = create_registered(self.manager, self.store, '本地', 'CBMC', None)
        self.assertIsNone(json.loads((config.VIP_TASK_DIR / local['task_id'] / 'task.json').read_text())['keti5'])

    async def test_pause_resume_upload_and_precision(self):
        first, second = self.create(), self.create()
        (first.task_dir / 'input' / '中文.c').write_text('内容')
        await self.manager.keti5.progress(PARAMS, 98)
        self.status(first, 'completed')
        await self.manager.keti5.task_finished(first.task_id)
        self.status(second, 'paused')
        await self.manager.keti5.task_finished(second.task_id)
        self.assertEqual([r['progress'] for r in records if 'progress' in r], [98])
        self.assertIn(first.task_id + '/input/中文.c', records[1]['files'])
        self.assertEqual(records[0]['buildId'], int(PARAMS['buildId']))
        self.assertEqual(records[1]['buildId'], PARAMS['buildId'])
        self.status(second, 'failed')
        await self.manager.keti5.task_finished(second.task_id)
        await self.manager.keti5.complete(('keti2', '123', 'batch'), PARAMS)
        self.assertEqual([r['progress'] for r in records if 'progress' in r], [98, 100])
        self.assertEqual(Task._metadata(first.task_dir)['keti5'], PARAMS)

    async def test_upload_failure_retry_and_cleanup(self):
        task = self.create()
        temporary = []
        original = keti5.task_archive
        def archive(task_id):
            result = original(task_id)
            temporary.append(result)
            return result
        with patch.object(keti5, 'task_archive', archive):
            with patch.object(config, 'KETI5_UPLOAD_URL', f'http://127.0.0.1:{self.port}/missing'):
                with self.assertRaises(Exception):
                    await keti5.upload(task.task_id)
            self.assertTrue(Task._metadata(task.task_dir)['keti5_upload_failed'])
            await keti5.upload(task.task_id)
            await keti5.upload(task.task_id)
        self.assertFalse(Task._metadata(task.task_dir)['keti5_upload_failed'])
        self.assertTrue(all(not path.exists() for path in temporary))
        self.assertEqual(len(records), 2)

    async def test_manual_endpoint_and_local_rejection(self):
        api = FastAPI()
        api.include_router(router)
        task = self.create()
        with TestClient(api) as client:
            response = client.post('/task/upload_to_factory', params={'task_id': task.task_id})
            self.assertEqual(response.status_code, 200)
            with patch.object(config, 'KETI5_UPLOAD_URL', ''):
                self.assertEqual(client.post('/task/upload_to_factory', params={'task_id': task.task_id}).status_code, 502)
            local = self.create(None)
            self.assertEqual(client.post('/task/upload_to_factory', params={'task_id': local.task_id}).status_code, 400)

    async def test_project_orchestration_and_resume(self):
        class Sources:
            def search(self, project_id):
                return [{'ipId': 'one'}, {'ipId': 'two'}]
            def collect(self, item, directory):
                (directory / 'input' / 'test.c').write_text('int main(){}')
        projects = ProjectManager(self.manager, self.store, keti2_sources=Sources())
        calls = 0
        async def run(task):
            nonlocal calls
            calls += 1
            self.status(task, 'paused' if calls == 1 else 'completed')
        with patch.object(Task, 'run', run):
            await projects.submit('123', keti5=PARAMS)
            await asyncio.gather(*projects.jobs.values())
            self.assertEqual([r['progress'] for r in records if 'progress' in r], [98])
            paused = next(task for task in self.manager.tasks.values() if Task._metadata(task.task_dir)['status'] == 'paused')
            self.manager._schedule(paused)
            await paused.job
        self.assertEqual([r['progress'] for r in records if 'progress' in r], [98, 100])
        self.assertEqual(sum('files' in record for record in records), 3)

    async def test_cancellation_uploads_and_completes(self):
        task = self.create()
        entered = asyncio.Event()
        async def run():
            entered.set()
            await asyncio.Event().wait()
        with patch.object(task, 'run', run):
            self.manager._schedule(task)
            await entered.wait()
            task.job.cancel()
            await asyncio.gather(task.job, return_exceptions=True)
        self.assertEqual(Task._metadata(task.task_dir)['verification_status'], 'cancelled')
        self.assertEqual(sum('files' in record for record in records), 1)
        self.assertEqual([r['progress'] for r in records if 'progress' in r], [100])

    async def test_preparation_failures_upload_before_completion(self):
        class Sources:
            def search(self, project_id):
                return [{'ipId': 'one'}, {'ipId': 'two'}]
            def collect(self, item, directory):
                raise ValueError('输入准备失败')
        projects = ProjectManager(self.manager, self.store, keti2_sources=Sources())
        await projects.submit('123', keti5=PARAMS)
        await asyncio.gather(*projects.jobs.values())
        self.assertEqual([r.get('progress', 'zip') for r in records], [98, 'zip', 'zip', 100])

    async def test_failed_requests_do_not_change_verification(self):
        task = self.create()
        async def run():
            self.status(task, 'completed')
        with patch.object(task, 'run', run), patch.multiple(config,
            KETI5_UPLOAD_URL=f'http://127.0.0.1:{self.port}/missing',
            KETI5_CALLBACK_URL=f'http://127.0.0.1:{self.port}/missing',
        ):
            self.manager._schedule(task)
            await task.job
        self.assertEqual(Task._metadata(task.task_dir)['verification_status'], 'completed')
        self.assertTrue(Task._metadata(task.task_dir)['keti5_upload_failed'])
        self.assertEqual(records, [])

    async def test_without_parameters_has_no_requests(self):
        task = self.create(None)
        self.status(task, 'completed')
        await self.manager.keti5.task_finished(task.task_id)
        self.assertEqual(records, [])
        self.assertNotIn('keti5_upload_failed', Task._metadata(task.task_dir))

    async def test_upload_never_overwrites_terminal_metadata(self):
        task = self.create()
        self.status(task, 'running')
        entered, release = threading.Event(), threading.Event()
        def slow_upload(task_id, params):
            entered.set()
            release.wait(2)
        with patch.object(keti5, '_upload', slow_upload):
            operation = asyncio.create_task(keti5.upload(task.task_id))
            self.assertTrue(await asyncio.to_thread(entered.wait, 2))
            self.status(task, 'completed')
            release.set()
            await operation
        self.assertEqual(Task._metadata(task.task_dir)['verification_status'], 'completed')
        self.assertFalse(Task._metadata(task.task_dir)['keti5_upload_failed'])

    async def test_cancelling_upload_still_checks_batch_completion(self):
        task = self.create()
        self.status(task, 'completed')
        entered, release = threading.Event(), threading.Event()
        def slow_upload(task_id, params):
            entered.set()
            release.wait(2)
        with patch.object(keti5, '_upload', slow_upload):
            operation = asyncio.create_task(self.manager.keti5.task_finished(task.task_id))
            self.assertTrue(await asyncio.to_thread(entered.wait, 2))
            operation.cancel()
            release.set()
            result = await asyncio.gather(operation, return_exceptions=True)
        self.assertIsInstance(result[0], asyncio.CancelledError)
        self.assertEqual([r['progress'] for r in records], [100])
        self.assertFalse(Task._metadata(task.task_dir)['keti5_upload_failed'])

    async def test_queued_resume_cancelled_before_coroutine_starts(self):
        task = self.create()
        self.status(task, 'paused')
        task.chat_mode = True
        self.manager._schedule(task)
        await self.manager.close()
        self.assertEqual(Task._metadata(task.task_dir)['verification_status'], 'cancelled')
        self.assertEqual([r.get('progress', 'zip') for r in records], ['zip', 100])

    async def test_restart_marks_interrupted_resume_terminal(self):
        task = self.create()
        self.status(task, 'paused')
        task.set_status('queued')
        recovered = TaskManager()
        self.assertEqual(recovered.interrupted, [task.task_id])
        self.assertEqual(Task._metadata(task.task_dir)['verification_status'], 'cancelled')

    def local_dataset(self):
        dataset = self.root / 'dataset'
        (dataset / 'ip' / '测试IP').mkdir(parents=True)
        (dataset / 'include').mkdir()
        (dataset / 'ip' / '测试IP' / 'main.c').write_text('int main(){}')
        (dataset / 'include' / 'common.h').write_text('#pragma once')
        return dataset

    async def test_local_api_keeps_factory_id_and_uploads(self):
        dataset = self.local_dataset()
        params = {**PARAMS, 'projectId': '0002059824406008037378'}
        api = FastAPI()
        api.include_router(router)
        api.state.task_manager = self.manager
        api.state.project_manager = SimpleNamespace(store=self.store)
        async def run(task):
            self.status(task, 'completed')
        with patch.object(config, 'VIP_DATASET_DIR', dataset), patch.object(Task, 'run', run):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api), base_url='http://test') as client:
                response = await client.post('/task/create_task', json={
                    'ip_name': '测试IP', 'tool': 'CBMC', 'keti5': params,
                })
            self.assertEqual(response.status_code, 201)
            task_id = response.json()['task_id']
            task = self.manager.tasks[task_id]
            await task.job
        entry = self.store.all_entries()[0]
        self.assertEqual(entry['projectID'], params['projectId'])
        self.assertIsNone(entry['keti'])
        self.assertEqual(Task._metadata(task.task_dir)['keti5'], params)
        self.assertTrue((task.task_dir / 'input' / 'ip' / '测试IP' / 'main.c').is_file())
        self.assertTrue((task.task_dir / 'input' / 'include' / 'common.h').is_file())
        self.assertEqual([r.get('progress', 'zip') for r in records], [98, 'zip', 100])
        self.assertFalse(Task._metadata(task.task_dir)['keti5_upload_failed'])
        await keti5.upload(task_id)
        self.assertEqual(len(records), 4)

    async def test_local_partial_parameters_preserve_original_behavior(self):
        dataset = self.local_dataset()
        async def run(task):
            self.status(task, 'completed')
        with patch.object(config, 'VIP_DATASET_DIR', dataset), patch.object(Task, 'run', run):
            for params in [None, {'projectId': '123'}]:
                result = await create_local(self.manager, self.store, '测试IP', 'CBMC', None, keti5=params)
                task = self.manager.tasks[result['task_id']]
                await task.job
                self.assertIsNone(Task._metadata(task.task_dir)['keti5'])
        self.assertTrue(all(row['projectID'] is None and row['keti'] is None for row in self.store.all_entries()))
        self.assertEqual(records, [])

    async def test_local_pause_and_resume_share_factory_lifecycle(self):
        dataset = self.local_dataset()
        count = 0
        async def run(task):
            nonlocal count
            count += 1
            self.status(task, 'paused' if count == 1 else 'completed')
        with patch.object(config, 'VIP_DATASET_DIR', dataset), patch.object(Task, 'run', run):
            result = await create_local(self.manager, self.store, '测试IP', 'CBMC', None, keti5=PARAMS)
            task = self.manager.tasks[result['task_id']]
            await task.job
            self.assertEqual([r.get('progress', 'zip') for r in records], [98, 'zip'])
            self.manager._schedule(task)
            await task.job
        self.assertEqual([r.get('progress', 'zip') for r in records], [98, 'zip', 'zip', 100])

    async def test_local_preparation_failure_uploads_before_rollback(self):
        dataset = self.local_dataset()
        with patch.object(config, 'VIP_DATASET_DIR', dataset), patch(
            'app.vip_task.inputs.collect_local', side_effect=ValueError('复制失败')
        ):
            with self.assertRaises(ValueError):
                await create_local(self.manager, self.store, '测试IP', 'CBMC', None, keti5=PARAMS)
        self.assertEqual([r.get('progress', 'zip') for r in records], [98, 'zip', 100])
        self.assertEqual(self.store.all_entries(), [])

    async def test_factory_errors_keep_full_json_in_log_and_frontend(self):
        task = self.create()
        payload = {'code': 500, 'success': False, 'message': '流水线不存在，请更换流水线名称',
                   'result': {'details': '完整错误' * 2000, 'buildId': int(PARAMS['buildId'])}}
        body = json.dumps(payload, ensure_ascii=False, indent=2)
        def reject(task_id, params):
            keti5._check_response(httpx.Response(200, text=body), '上传', 'code', 200)
        api = FastAPI()
        api.include_router(router)
        with patch.object(keti5, '_upload', reject), self.assertLogs('app', level='INFO') as logs:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api), base_url='http://test') as client:
                response = await client.post('/task/upload_to_factory', params={'task_id': task.task_id})
        self.assertEqual(response.status_code, 502)
        detail = response.json()['detail']
        self.assertIn('HTTP 200', detail)
        self.assertIn(body, detail)
        self.assertIn(body, '\n'.join(logs.output))
        self.assertTrue(Task._metadata(task.task_dir)['keti5_upload_failed'])

    async def test_http_and_invalid_json_errors_keep_response_text(self):
        for status, body in [(403, '<html>需要认证</html>'), (200, '不是JSON'),
                             (200, '[]'), (200, 'null'), (200, '{"success":false,"message":"执行不存在"}')]:
            with self.subTest(status=status, body=body):
                with self.assertRaises(ValueError) as raised:
                    keti5._check_response(httpx.Response(status, text=body), '进度推送', 'success', True)
                self.assertIn(body, str(raised.exception))
                self.assertIn(f'HTTP {status}', str(raised.exception))

    async def test_connection_error_details_reach_frontend(self):
        task = self.create()
        api = FastAPI()
        api.include_router(router)
        with patch.object(keti5, '_upload', side_effect=httpx.ConnectError('Connection refused')):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api), base_url='http://test') as client:
                response = await client.post('/task/upload_to_factory', params={'task_id': task.task_id})
        self.assertEqual(response.status_code, 502)
        self.assertIn('ConnectError', response.json()['detail'])
        self.assertIn('Connection refused', response.json()['detail'])

    async def test_actual_resume_failure_becomes_terminal(self):
        task = self.create()
        self.status(task, 'paused')
        task.chat_mode = True
        async def events(prompt):
            yield {'type': 'error', 'error': '验证失败'}
        with patch.object(task, '_agent_events', events):
            await task.async_run('继续')
        self.assertEqual(Task._metadata(task.task_dir)['verification_status'], 'failed')


if __name__ == '__main__':
    unittest.main()
