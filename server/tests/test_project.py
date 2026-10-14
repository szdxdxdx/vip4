"""项目 API、文件来源和生命周期测试；网络和 Pi 均使用替身。"""
import asyncio
import csv
import io
import json
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch, Mock, AsyncMock

from fastapi.testclient import TestClient

from app.vip_task import config
from app.vip_task.keti2_sources import Keti2Sources, Keti2Config, FIELDS
from app.vip_task.project import ProjectManager, ProjectStore, ProjectConflictError, ProjectNotFoundError
from app.vip_task.task import Task, _write_metadata
from app.vip_task.task_manager import TaskManager
from main import create_app


def item(c, h=None, ip_id='B_TcProcess'):
    return {'ipId': 'ip-1', 'ipMsg': {
        'entity': {'basicInformation': {'id': ip_id, 'name': '不应记录的名称'},
                   'entityImplementation': {'dotC': str(c), 'dotH': str(h) if h else '无'}},
        'formalModel': {'stateMachine': '', 'contracts': None, 'invariant': ' 无 ',
                        'nonfunctionalConstraint': ''}}}


def status(task, value):
    path = task.task_dir / 'task.json'
    metadata = json.loads(path.read_text())
    metadata['status'] = value
    _write_metadata(path, metadata)


class Keti2SourceTests(unittest.TestCase):
    def test_search_schema_and_encoded_project_id(self):
        sources = Keti2Sources(Keti2Config())
        with patch('app.vip_task.keti2_sources.urlopen', return_value=io.BytesIO(
            json.dumps({'code': 0, 'result': [item('/a.c')]}).encode())) as network:
            self.assertEqual(len(sources.search('中文 &1')), 1)
            self.assertIn('projectId=%E4%B8%AD%E6%96%87%20%261', network.call_args.args[0])
        for payload in ({'code': 1, 'result': []}, {'code': 0, 'result': {}},
                        {'code': 0, 'result': [{}]}):
            with patch('app.vip_task.keti2_sources.urlopen', return_value=io.BytesIO(json.dumps(payload).encode())):
                with self.assertRaises(ValueError):
                    sources.search('p')

    def test_fields_mapping_csv_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / 'original'
            original.mkdir()
            (original / 'code.c').write_text('C')
            (original / 'code.h').write_text('H')
            task = root / 'task'
            task.mkdir()
            data = item('/uploads/code.c', '/uploads/code.h')
            data['ipMsg']['formalModel']['contracts'] = [None, '无', '', '/uploads/code.c']
            data['ignored'] = '/missing'
            sources = Keti2Sources(Keti2Config(path_map={'/uploads': str(original)}))
            sources.collect(data, task)
            with (task / 'files.csv').open() as f:
                rows = list(csv.DictReader(f))
            self.assertEqual([r['field'] for r in rows], [FIELDS[0], FIELDS[1], FIELDS[3]])
            paths = [Path(r['path']) for r in rows]
            self.assertEqual(len(set(paths)), 3)
            self.assertTrue(all(p.is_absolute() and p.parent == task / 'input' for p in paths))
            self.assertEqual([p.read_text() for p in paths], ['C', 'H', 'C'])
            self.assertEqual(paths[0].name, 'code.c')
            self.assertEqual(paths[1].name, 'code.h')

    def test_partial_collection_has_manifest_and_missing_task_is_not_recreated(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'code.c'
            source.write_text('C')
            task = root / 'task'
            task.mkdir()
            sources = Keti2Sources(Keti2Config(download_url=''))
            with self.assertRaises(FileNotFoundError):
                sources.collect(item(source, root / 'missing.h'), task)
            with (task / 'files.csv').open() as manifest:
                rows = list(csv.DictReader(manifest))
            self.assertEqual(len(rows), 1)
            self.assertEqual(Path(rows[0]['path']).read_text(), 'C')
            missing = root / 'deleted-task'
            with self.assertRaises(FileNotFoundError):
                sources.collect(item(source), missing)
            self.assertFalse(missing.exists())

    def test_http_post_download_and_explicit_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / 'target'
            sources = Keti2Sources(Keti2Config(timeout=7))
            with patch('app.vip_task.keti2_sources.urlopen', return_value=io.BytesIO(b'url-data')) as network:
                sources._copy('https://host/file.c', target)
                self.assertEqual(network.call_args.args[0], 'https://host/file.c')
            self.assertEqual(target.read_bytes(), b'url-data')
            source = '/software/software-ip-backend/files/ip-integrated-files/345/模式切换指令处理/entity/EntityImplementation/code.h'
            content = b'\x00\xffheader-data'
            with patch('app.vip_task.keti2_sources.urlopen', return_value=io.BytesIO(content)) as network:
                sources._copy(source, target)
                request = network.call_args.args[0]
                self.assertEqual(request.full_url, 'http://8.130.30.48:8877/api/file/downloadFile')
                self.assertEqual(request.get_method(), 'POST')
                self.assertEqual(request.get_header('Content-type'), 'application/json')
                self.assertEqual(json.loads(request.data.decode('utf-8')), {'filePath': source})
                self.assertEqual(network.call_args.kwargs['timeout'], 7)
            self.assertEqual(target.read_bytes(), content)
            target.unlink()
            with patch('app.vip_task.keti2_sources.urlopen', side_effect=HTTPError(
                    sources.config.download_url, 404, 'Not Found', {}, None)):
                with self.assertRaises(HTTPError):
                    sources._copy(source, target)
            self.assertFalse(target.exists())
            sources.config.download_url = ''
            with self.assertRaises(FileNotFoundError):
                sources._copy('/unavailable/a.c', target)
            sources.config.path_map = {'/uploads': str(root)}
            with self.assertRaises(ValueError):
                sources._copy('/uploads/../escape', target)
            (root / 'empty').mkdir()
            with self.assertRaises(ValueError):
                sources.collect(item('无'), root / 'empty')

    def test_post_collection_saves_input_and_original_source_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            task = Path(temporary) / 'task'
            task.mkdir()
            source = '/software/software-ip-backend/files/模式切换指令处理/code.c'
            data = b'int main(void) { return 0; }'
            with patch('app.vip_task.keti2_sources.urlopen', return_value=io.BytesIO(data)) as network:
                Keti2Sources(Keti2Config()).collect(item(source), task)
            self.assertEqual(json.loads(network.call_args.args[0].data), {'filePath': source})
            with (task / 'files.csv').open(encoding='utf-8') as manifest:
                rows = list(csv.DictReader(manifest))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['source'], source)
            self.assertEqual(rows[0]['field'], FIELDS[0])
            self.assertEqual(Path(rows[0]['path']), task / 'input' / 'code.c')
            self.assertEqual(Path(rows[0]['path']).read_bytes(), data)

    def test_urls_use_config_and_local_files_do_not_use_network(self):
        with patch.object(config, 'KETI2_SEARCH_URL', 'https://new-host/search'), \
             patch.object(config, 'KETI2_DOWNLOAD_URL', 'https://new-host/download'), \
             patch.dict('os.environ', {'VIP_SOURCE_DOWNLOAD_URL': 'https://ignored/download',
                                      'VIP_PROJECT_SEARCH_URL': 'https://ignored/search',
                                      'VIP_SOURCE_PATH_MAP': '{}'}):
            settings = Keti2Config.from_env()
            self.assertEqual(settings.search_url, 'https://new-host/search')
            self.assertEqual(settings.download_url, 'https://new-host/download')
            self.assertEqual(Keti2Config().download_url, 'https://new-host/download')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source.c'
            source.write_bytes(b'local')
            sources = Keti2Sources(Keti2Config(path_map={'/uploads': str(root)}))
            with patch('app.vip_task.keti2_sources.urlopen', side_effect=AssertionError('禁止网络请求')):
                sources._copy(str(source), root / 'direct.c')
                sources._copy('/uploads/source.c', root / 'mapped.c')
            self.assertEqual((root / 'direct.c').read_bytes(), b'local')
            self.assertEqual((root / 'mapped.c').read_bytes(), b'local')


class StoreTests(unittest.TestCase):
    def test_old_schema_migration_preserves_rows_and_only_adds_ip_id(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'mapping.sqlite3'
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE project_tasks (task_id TEXT PRIMARY KEY, projectID TEXT NOT NULL)')
                db.execute("INSERT INTO project_tasks VALUES ('old', 'project')")
            store = ProjectStore(path)
            try:
                self.assertEqual(store.entries('project'), [{'task_id': 'old', 'ip_id': ''}])
                store.add('new', 'project', 'B_TcProcess')
                columns = {row[1] for row in store.db.execute('PRAGMA table_info(project_tasks)')}
                self.assertEqual(columns, {'task_id', 'projectID', 'ip_id', 'keti'})
            finally:
                store.close()
            restored = ProjectStore(path)
            try:
                self.assertEqual(restored.entries('project'), [
                    {'task_id': 'old', 'ip_id': ''}, {'task_id': 'new', 'ip_id': 'B_TcProcess'}])
            finally:
                restored.close()


class ProjectTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patcher = patch.object(config, 'VIP_TASK_DIR', self.root / 'tasks')
        self.patcher.start()
        self.source = self.root / 'ip.c'
        self.source.write_text('int main(void) {return 0;}')
        self.tasks = TaskManager()
        self.keti2_sources = Keti2Sources(Keti2Config(download_url=''))
        self.manager = ProjectManager(self.tasks, ProjectStore(self.root / 'mapping.sqlite3'), self.keti2_sources)

    async def asyncTearDown(self):
        await self.manager.close()
        await self.tasks.close()
        self.patcher.stop()
        self.temp.cleanup()

    async def test_all_inputs_ready_then_serial_results_and_restart(self):
        started = []
        async def fake_run(task):
            ids = self.manager.store.tasks('项目', keti='keti2')
            self.assertEqual(len(ids), 2)
            self.assertTrue(all((config.VIP_TASK_DIR / i / 'files.csv').is_file() for i in ids))
            self.assertIn('CBMC', task.prompt)
            self.assertIn(str(task.task_dir.resolve() / 'input'), task.prompt)
            started.append(task.task_id)
            status(task, 'running')
            output = task.task_dir / 'workspace' / 'cbmc_suite' / 'output'
            output.mkdir(parents=True)
            (output / 'report.json').write_text('{}')
            (task.task_dir / 'workspace' / 'not-result.txt').write_text('not result')
            await asyncio.sleep(.001)
            status(task, 'completed')
        with patch.object(self.keti2_sources, 'search', return_value=[item(self.source, ip_id='B_First'), item(self.source, ip_id='B_Second')]), \
             patch.object(Task, 'run', fake_run):
            self.assertEqual((await self.manager.submit('项目'))['status'], 'accepted')
            with self.assertRaises(ProjectConflictError):
                await self.manager.submit('项目')
            await self.manager.jobs[('keti2', '项目')]
        progress = self.manager.progress('项目', source='keti2')
        self.assertEqual((progress['status'], progress['total'], progress['finished']), ('completed', 2, 2))
        self.assertEqual(started, self.manager.store.tasks('项目', keti='keti2'))
        self.assertEqual([t['ip_id'] for t in progress['tasks']], ['B_First', 'B_Second'])
        self.assertTrue(all(len(i) == 8 and i[:4].isdigit() and i[4:].isalnum() for i in started))
        result = self.manager.results('项目', source='keti2')
        self.assertEqual([t['ip_id'] for t in result['tasks']], ['B_First', 'B_Second'])
        self.assertEqual(len(result['tasks'][0]['files']), 1)
        self.assertTrue(result['tasks'][0]['files'][0]['download_url'].startswith('/task/get_file?'))
        with self.assertRaises(ProjectConflictError):
            await self.manager.submit('项目')
        restored = ProjectManager(self.tasks, ProjectStore(self.root / 'mapping.sqlite3'), self.keti2_sources)
        try:
            self.assertEqual(restored.progress('项目', source='keti2')['status'], 'completed')
            self.assertEqual([t['ip_id'] for t in restored.progress('项目', source='keti2')['tasks']], ['B_First', 'B_Second'])
            self.assertEqual(restored.results('项目', source='keti2'), result)
            with self.assertRaises(ProjectConflictError):
                await restored.submit('项目')
        finally:
            await restored.close()

    async def test_missing_or_nonstring_business_id_does_not_block_tasks(self):
        values = [item(self.source, ip_id=None), item(self.source, ip_id=345), item(self.source)]
        del values[2]['ipMsg']['entity']['basicInformation']
        async def fake_run(task):
            status(task, 'completed')
        with patch.object(self.keti2_sources, 'search', return_value=values), patch.object(Task, 'run', fake_run):
            await self.manager.submit('missing-id')
            await self.manager.jobs[('keti2', 'missing-id')]
        progress = self.manager.progress('missing-id', source='keti2')
        self.assertEqual(progress['status'], 'completed')
        self.assertEqual([task['ip_id'] for task in progress['tasks']], ['', '', ''])

    async def test_empty_and_network_failure(self):
        with patch.object(self.keti2_sources, 'search', return_value=[]):
            await self.manager.submit('empty')
            await self.manager.jobs[('keti2', 'empty')]
        self.assertEqual(self.manager.progress('empty', source='keti2'), {
            'projectID': 'empty', 'keti': 'keti2', 'status': 'empty', 'source': 'keti2', 'total': 0, 'finished': 0, 'tasks': []})
        with patch.object(self.keti2_sources, 'search', side_effect=OSError('network failed')):
            await self.manager.submit('bad')
            await self.manager.jobs[('keti2', 'bad')]
        self.assertEqual(self.manager.progress('bad', source='keti2')['error'], 'network failed')

    async def test_collection_failure_does_not_skip_other_ips(self):
        async def fake_run(task):
            status(task, 'completed')
        with patch.object(self.keti2_sources, 'search', return_value=[item('/missing/a.c'), item(self.source)]), \
             patch.object(Task, 'run', fake_run):
            await self.manager.submit('broken')
            await self.manager.jobs[('keti2', 'broken')]
        progress = self.manager.progress('broken', source='keti2')
        self.assertEqual(progress['status'], 'failed')
        self.assertEqual(progress['total'], 2)
        self.assertEqual([t['status'] for t in progress['tasks']], ['failed', 'completed'])

    async def test_shutdown_cancels_running_and_waiting(self):
        entered = asyncio.Event()
        async def fake_run(task):
            status(task, 'running')
            entered.set()
            await asyncio.Event().wait()
        with patch.object(self.keti2_sources, 'search', return_value=[item(self.source), item(self.source)]), \
             patch.object(Task, 'run', fake_run):
            await self.manager.submit('shutdown')
            await entered.wait()
            job = self.manager.jobs[('keti2', 'shutdown')]
            job.cancel()
            await asyncio.gather(job, return_exceptions=True)
        self.assertEqual(self.manager.progress('shutdown', source='keti2')['status'], 'cancelled')
        self.assertTrue(all(t['status'] == 'cancelled' for t in self.manager.progress('shutdown', source='keti2')['tasks']))

    async def test_deleting_one_task_continues_remaining(self):
        entered = asyncio.Event()
        started = []
        async def fake_run(task):
            started.append(task.task_id)
            if len(started) == 1:
                status(task, 'running')
                entered.set()
                await asyncio.Event().wait()
            status(task, 'completed')
        with patch.object(self.keti2_sources, 'search', return_value=[item(self.source), item(self.source)]), \
             patch.object(Task, 'run', fake_run):
            await self.manager.submit('delete-one')
            await entered.wait()
            await self.tasks.delete_task(started[0])
            await self.manager.jobs[('keti2', 'delete-one')]
        progress = self.manager.progress('delete-one', source='keti2')
        self.assertEqual(len(started), 2)
        self.assertEqual(progress['status'], 'completed')
        self.assertEqual(len(progress['tasks']), 1)
        self.assertEqual(progress['tasks'][0]['status'], 'completed')
        self.assertFalse(self.manager.store.has_task(started[0]))

    async def test_progress_does_not_scan_workspace(self):
        with patch.object(self.keti2_sources, 'search', return_value=[item(self.source)]):
            await self.manager.submit('metadata-only')
            self.manager.jobs[('keti2', 'metadata-only')].cancel()
            await asyncio.gather(self.manager.jobs[('keti2', 'metadata-only')], return_exceptions=True)
        self.manager._create(('keti2', 'metadata-only'), None, 'B_Meta')
        with patch.object(self.tasks, 'get_task', side_effect=AssertionError('不应扫描 workspace')):
            self.assertEqual(self.manager.progress('metadata-only', source='keti2')['total'], 1)

    async def test_chat_status_does_not_overwrite_project_verification(self):
        task_id = self.manager._create(('keti2', 'chat-project'), None, 'B_Chat')
        path = config.VIP_TASK_DIR / task_id / 'task.json'
        metadata = json.loads(path.read_text())
        metadata.update(status='idle', chatstatus='idle', verification_status='completed')
        _write_metadata(path, metadata)
        self.manager.projects[('keti2', 'chat-project')] = {'status': 'completed'}
        task = self.manager.progress('chat-project', source='keti2')['tasks'][0]
        self.assertEqual(task['status'], 'completed')
        self.assertEqual(task['chatstatus'], 'idle')
        self.assertEqual(self.manager.progress('chat-project', source='keti2')['finished'], 1)
        self.manager.projects[('keti2', 'chat-project')] = {'status': 'failed', 'error': '旧任务未完成'}
        progress = self.manager.progress('chat-project', source='keti2')
        self.assertEqual(progress['status'], 'completed')
        self.assertNotIn('error', progress)

    async def test_force_completed_project_cleans_files_and_mapping_only_for_target(self):
        async def fake_run(task):
            status(task, 'completed')
        with patch.object(self.keti2_sources, 'search', return_value=[item(self.source)]), patch.object(Task, 'run', fake_run):
            await self.manager.submit('target')
            await self.manager.jobs[('keti2', 'target')]
            await self.manager.submit('other')
            await self.manager.jobs[('keti2', 'other')]
            old = self.manager.store.tasks('target', keti='keti2')[0]
            other = self.manager.store.tasks('other', keti='keti2')[0]
            old_directory = config.VIP_TASK_DIR / old
            (old_directory / 'workspace' / 'old-result.txt').write_text('旧报告')
            self.assertEqual((await self.manager.submit('target', force=True))['status'], 'accepted')
            self.assertFalse(old_directory.exists())
            self.assertFalse(self.manager.store.has_task(old))
            self.assertTrue((config.VIP_TASK_DIR / other).exists())
            await self.manager.jobs[('keti2', 'target')]
            self.assertEqual(len(self.manager.store.tasks('target', keti='keti2')), 1)
            self.assertEqual(self.manager.progress('other', source='keti2')['status'], 'completed')

    async def test_force_running_project_waits_for_resource_cleanup(self):
        entered = asyncio.Event()
        released = asyncio.Event()
        calls = 0
        async def fake_run(task):
            nonlocal calls
            calls += 1
            if calls == 1:
                entered.set()
                try:
                    await asyncio.Event().wait()
                finally:
                    released.set()
            else:
                status(task, 'completed')
        with patch.object(self.keti2_sources, 'search', return_value=[item(self.source), item(self.source)]), patch.object(Task, 'run', fake_run):
            await self.manager.submit('running-force')
            await entered.wait()
            old = self.manager.store.tasks('running-force', keti='keti2')
            await self.manager.submit('running-force', force=True)
            self.assertTrue(released.is_set())
            self.assertTrue(all(not (config.VIP_TASK_DIR / task_id).exists() for task_id in old))
            await self.manager.jobs[('keti2', 'running-force')]
        self.assertEqual(self.manager.progress('running-force', source='keti2')['status'], 'completed')

    async def test_force_during_collection_waits_and_blocks_second_submission(self):
        entered = threading.Event()
        release = threading.Event()
        calls = 0
        collect = self.keti2_sources.collect
        def slow_collect(*args):
            nonlocal calls
            calls += 1
            if calls == 1:
                entered.set()
                if not release.wait(5):
                    raise TimeoutError('测试收集未释放')
            return collect(*args)
        async def fake_run(task):
            status(task, 'completed')
        with patch.object(self.keti2_sources, 'search', return_value=[item(self.source)]), patch.object(self.keti2_sources, 'collect', slow_collect), patch.object(Task, 'run', fake_run):
            await self.manager.submit('collect-force')
            await asyncio.to_thread(entered.wait, 5)
            old = self.manager.store.tasks('collect-force', keti='keti2')
            replacement = asyncio.create_task(self.manager.submit('collect-force', force=True))
            try:
                await asyncio.sleep(.01)
                self.assertFalse(replacement.done())
                self.assertEqual(self.manager.progress('collect-force', source='keti2')['status'], 'resetting')
                with self.assertRaises(ProjectConflictError):
                    await self.manager.submit('collect-force', force=True)
                with self.assertRaises(ProjectConflictError):
                    await self.manager.submit('collect-force')
            finally:
                release.set()
                await replacement
            self.assertTrue(all(not (config.VIP_TASK_DIR / task_id).exists() for task_id in old))
            await self.manager.jobs[('keti2', 'collect-force')]
        self.assertEqual(self.manager.progress('collect-force', source='keti2')['status'], 'completed')

    async def test_force_cleanup_failure_keeps_mapping_and_allows_retry(self):
        async def fake_run(task):
            status(task, 'completed')
        with patch.object(self.keti2_sources, 'search', return_value=[item(self.source)]), patch.object(Task, 'run', fake_run):
            await self.manager.submit('retry-force')
            await self.manager.jobs[('keti2', 'retry-force')]
            old = self.manager.store.tasks('retry-force', keti='keti2')
            with patch.object(self.tasks, 'delete_task', side_effect=PermissionError('禁止删除')):
                with self.assertRaises(PermissionError):
                    await self.manager.submit('retry-force', force=True)
            self.assertEqual(self.manager.store.tasks('retry-force', keti='keti2'), old)
            self.assertEqual(self.manager.progress('retry-force', source='keti2')['status'], 'failed')
            await self.manager.submit('retry-force', force=True)
            await self.manager.jobs[('keti2', 'retry-force')]
        self.assertEqual(self.manager.progress('retry-force', source='keti2')['status'], 'completed')

    async def test_repeated_request_cancellation_does_not_interrupt_force_cleanup(self):
        async def fake_run(task):
            status(task, 'completed')
        entered = asyncio.Event()
        release = asyncio.Event()
        delete = self.tasks.delete_task
        with patch.object(self.keti2_sources, 'search', return_value=[item(self.source), item(self.source)]), patch.object(Task, 'run', fake_run):
            await self.manager.submit('cancel-force')
            await self.manager.jobs[('keti2', 'cancel-force')]
            old = self.manager.store.tasks('cancel-force', keti='keti2')
            async def delayed_delete(task_id):
                if task_id == old[1]:
                    entered.set()
                    await release.wait()
                return await delete(task_id)
            with patch.object(self.tasks, 'delete_task', delayed_delete):
                request = asyncio.create_task(self.manager.submit('cancel-force', force=True))
                await entered.wait()
                operation = self.manager.resets[('keti2', 'cancel-force')]
                try:
                    request.cancel()
                    await asyncio.sleep(0)
                    request.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await request
                    self.assertIn(('keti2', 'cancel-force'), self.manager.resets)
                    self.assertFalse(operation.cancelled())
                    with self.assertRaises(ProjectConflictError):
                        await self.manager.submit('cancel-force', force=True)
                finally:
                    release.set()
                    await operation
            await self.manager.jobs[('keti2', 'cancel-force')]
            self.assertTrue(all(not self.manager.store.has_task(task_id) for task_id in old))
            self.assertTrue(all(not (config.VIP_TASK_DIR / task_id).exists() for task_id in old))

    async def test_partial_creation_failure_cannot_be_reported_as_completed(self):
        async def fake_run(task):
            status(task, 'completed')
        create = self.manager._create
        def failing_create(project_id, prompt, ip_id, ip_name, tool):
            if ip_id == 'B_Broken':
                raise OSError('无法创建任务')
            return create(project_id, prompt, ip_id, ip_name, tool)
        with patch.object(self.keti2_sources, 'search', return_value=[item(self.source, ip_id='B_Broken'), item(self.source, ip_id='B_Good')]), patch.object(self.manager, '_create', failing_create), patch.object(Task, 'run', fake_run):
            await self.manager.submit('partial-create', force=True)
            await self.manager.jobs[('keti2', 'partial-create')]
        progress = self.manager.progress('partial-create', source='keti2')
        self.assertEqual(progress['status'], 'failed')
        self.assertIn('创建失败', progress['error'])
        self.assertEqual(progress['tasks'][0]['status'], 'completed')
        self.assertNotIn('requires_resubmit', progress)

    async def test_force_unknown_project_is_accepted(self):
        with patch.object(self.keti2_sources, 'search', return_value=[]):
            await self.manager.submit('new-force', force=True)
            await self.manager.jobs[('keti2', 'new-force')]
        self.assertEqual(self.manager.progress('new-force', source='keti2')['status'], 'empty')

    async def test_delete_completed_and_cold_start_preserves_other_project(self):
        async def fake_run(task):
            status(task, 'completed')
        with patch.object(self.keti2_sources, 'search', return_value=[item(self.source), item(self.source)]), patch.object(Task, 'run', fake_run):
            await self.manager.submit('delete')
            await self.manager.jobs[('keti2', 'delete')]
            await self.manager.submit('keep')
            await self.manager.jobs[('keti2', 'keep')]
        old = self.manager.store.tasks('delete', keti='keti2')
        self.assertEqual(await self.manager.delete('delete', source='keti2'), {'projectID': 'delete', 'keti': 'keti2', 'status': 'deleted'})
        self.assertNotIn('delete', self.manager.projects)
        self.assertNotIn('delete', self.manager.jobs)
        self.assertTrue(all(i not in self.tasks.tasks and not (config.VIP_TASK_DIR / i).exists() for i in old))
        self.assertEqual(self.manager.store.tasks('delete', keti='keti2'), [])
        with self.assertRaises(ProjectNotFoundError):
            self.manager.progress('delete', source='keti2')
        with self.assertRaises(ProjectNotFoundError):
            await self.manager.delete('delete', source='keti2')
        cold_tasks = TaskManager()
        cold = ProjectManager(cold_tasks, ProjectStore(self.root / 'mapping.sqlite3'), self.keti2_sources)
        try:
            keep = cold.store.tasks('keep', keti='keti2')
            await cold.delete('keep', source='keti2')
            self.assertTrue(all(not (config.VIP_TASK_DIR / i).exists() for i in keep))
        finally:
            await cold.close()
            await cold_tasks.close()

    async def test_delete_running_waits_for_resource_release(self):
        entered, releasing, release, released = (asyncio.Event() for _ in range(4))
        async def fake_run(task):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                releasing.set()
                await release.wait()
                released.set()
        with patch.object(self.keti2_sources, 'search', return_value=[item(self.source), item(self.source)]), patch.object(Task, 'run', fake_run):
            await self.manager.submit('running-delete')
            await entered.wait()
            old = self.manager.store.tasks('running-delete', keti='keti2')
            request = asyncio.create_task(self.manager.delete('running-delete', source='keti2'))
            await releasing.wait()
            try:
                self.assertFalse(request.done())
                self.assertEqual(self.manager.progress('running-delete', source='keti2')['status'], 'deleting')
                self.assertTrue(all((config.VIP_TASK_DIR / i).exists() for i in old))
                for action in (self.manager.delete('running-delete', source='keti2'), self.manager.submit('running-delete'), self.manager.submit('running-delete', force=True)):
                    with self.assertRaises(ProjectConflictError):
                        await action
            finally:
                release.set()
                await request
            self.assertTrue(released.is_set())
            self.assertTrue(all(not (config.VIP_TASK_DIR / i).exists() for i in old))

    async def test_delete_during_search_or_collection_waits_for_threads(self):
        for phase in ('search', 'collect'):
            with self.subTest(phase=phase):
                entered, release = threading.Event(), threading.Event()
                project_id = 'delete-' + phase
                search = lambda _: [item(self.source)]
                collect = self.keti2_sources.collect
                def slow(*args):
                    entered.set()
                    if not release.wait(5):
                        raise TimeoutError('测试线程未释放')
                    return search(*args) if phase == 'search' else collect(*args)
                with patch.object(self.keti2_sources, 'search', slow if phase == 'search' else search), patch.object(self.keti2_sources, 'collect', slow if phase == 'collect' else collect), patch.object(Task, 'run', side_effect=AssertionError('不应启动 Pi')):
                    await self.manager.submit(project_id)
                    self.assertTrue(await asyncio.to_thread(entered.wait, 5))
                    request = asyncio.create_task(self.manager.delete(project_id, source='keti2'))
                    try:
                        await asyncio.sleep(.01)
                        self.assertFalse(request.done())
                        self.assertEqual(self.manager.progress(project_id, source='keti2')['status'], 'deleting')
                    finally:
                        release.set()
                        await request
                    self.assertEqual(self.manager.store.tasks(project_id, keti='keti2'), [])

    async def test_delete_partial_failure_keeps_all_mapping_and_can_retry(self):
        ids = [self.manager._create(('keti2', 'retry-delete'), None, 'B_Retry') for _ in range(2)]
        for task_id in ids:
            status(self.tasks.tasks[task_id], 'completed')
        delete = self.tasks.delete_task
        async def partial(task_id):
            if task_id == ids[1]:
                raise PermissionError('禁止删除')
            return await delete(task_id)
        with patch.object(self.tasks, 'delete_task', partial):
            with self.assertRaises(PermissionError):
                await self.manager.delete('retry-delete', source='keti2')
        self.assertEqual(self.manager.store.tasks('retry-delete', keti='keti2'), ids[1:])
        self.assertEqual(self.manager.progress('retry-delete', source='keti2')['status'], 'failed')
        self.assertNotIn('requires_resubmit', self.manager.progress('retry-delete', source='keti2'))
        self.assertFalse((config.VIP_TASK_DIR / ids[0]).exists())
        with self.assertRaises(ProjectConflictError):
            await self.manager.submit('retry-delete')
        await self.manager.delete('retry-delete', source='keti2')
        self.assertEqual(self.manager.store.tasks('retry-delete', keti='keti2'), [])

    async def test_repeated_delete_and_shutdown_cancellation_does_not_interrupt_cleanup(self):
        task_id = self.manager._create(('keti2', 'cancel-delete'), None, 'B_Cancel')
        entered, release = asyncio.Event(), asyncio.Event()
        delete = self.tasks.delete_task
        async def delayed(task_id):
            entered.set()
            await release.wait()
            return await delete(task_id)
        with patch.object(self.tasks, 'delete_task', delayed):
            request = asyncio.create_task(self.manager.delete('cancel-delete', source='keti2'))
            await entered.wait()
            operation = self.manager.resets[('keti2', 'cancel-delete')]
            request.cancel()
            await asyncio.sleep(0)
            request.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await request
            shutdown = asyncio.create_task(self.manager.close())
            await asyncio.sleep(0)
            shutdown.cancel()
            await asyncio.sleep(0)
            shutdown.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await shutdown
            try:
                self.assertFalse(operation.done())
                with self.assertRaises(ProjectConflictError):
                    await self.manager.submit('new')
                self.assertEqual(self.manager.store.tasks('cancel-delete', keti='keti2'), [task_id])
            finally:
                release.set()
                await self.manager.close()
        self.assertFalse((config.VIP_TASK_DIR / task_id).exists())
        self.assertNotIn('cancel-delete', self.manager.projects)
        self.assertNotIn('cancel-delete', self.manager.resets)

    async def test_force_shutdown_waits_for_cleanup_without_starting_new_job(self):
        task_id = self.manager._create(('keti2', 'close-force'), None, 'B_Close')
        entered, release = asyncio.Event(), asyncio.Event()
        delete = self.tasks.delete_task
        async def delayed(task_id):
            entered.set()
            await release.wait()
            return await delete(task_id)
        with patch.object(self.tasks, 'delete_task', delayed), patch.object(self.keti2_sources, 'search', side_effect=AssertionError('关闭期间禁止查询')):
            request = asyncio.create_task(self.manager.submit('close-force', force=True))
            await entered.wait()
            shutdown = asyncio.create_task(self.manager.close())
            await asyncio.sleep(0)
            release.set()
            with self.assertRaises(ProjectConflictError):
                await request
            await shutdown
        self.assertFalse((config.VIP_TASK_DIR / task_id).exists())
        self.assertEqual(self.manager.projects[('keti2', 'close-force')]['status'], 'failed')

    async def test_project_finalization_does_not_cancel_a_new_chat_job(self):
        task_id = self.manager._create(('keti2', 'chat-race'), None, 'B_Chat')
        task = self.tasks.tasks[task_id]
        path = task.task_dir / 'task.json'
        metadata = json.loads(path.read_text())
        task.job = asyncio.create_task(asyncio.Event().wait())
        try:
            for current in ('queued', 'running'):
                metadata.update(status=current, chatstatus=current, verification_status='completed')
                _write_metadata(path, metadata)
                self.manager._mark_unfinished(task_id)
                actual = json.loads(path.read_text())
                self.assertEqual(actual['status'], current)
                self.assertEqual(actual['chatstatus'], current)
                self.assertEqual(actual['verification_status'], 'completed')
        finally:
            task.job.cancel()
            await asyncio.gather(task.job, return_exceptions=True)

    async def test_keti3_validation_failure_preserves_force_target(self):
        task_id = self.manager._create(('keti2', '123'), None, 'B_Old')
        directory = config.VIP_TASK_DIR / task_id
        report = directory / 'workspace' / 'report.txt'
        report.write_text('旧结果')
        self.manager.keti3_sources = Mock()
        self.manager.keti3_sources.validate.side_effect = ValueError('课题三配置或 ID 无效')
        with patch.object(self.tasks, 'delete_task', new_callable=AsyncMock) as delete:
            with self.assertRaises(ValueError):
                await self.manager.submit('123', force=True, source='keti3')
            delete.assert_not_awaited()
        self.manager.keti3_sources.validate.assert_called_once_with('123')
        self.assertEqual(self.manager.store.tasks('123', keti='keti2'), [task_id])
        self.assertEqual(report.read_text(), '旧结果')
        self.assertNotIn('123', self.manager.resets)
        self.assertNotIn('123', self.manager.jobs)

    async def test_store_add_failure_rolls_back_unstarted_task(self):
        with patch.object(self.manager.store, 'add', side_effect=sqlite3.OperationalError('映射写入失败')), \
             patch.object(Task, 'run', side_effect=AssertionError('不应启动 Pi')):
            with self.assertRaises(sqlite3.OperationalError):
                self.manager._create(('keti2', 'rollback'), None, 'B_Rollback')
        self.assertEqual(self.manager.store.tasks('rollback', keti='keti2'), [])
        self.assertEqual(self.tasks.tasks, {})
        self.assertEqual(list(config.VIP_TASK_DIR.iterdir()), [])
        self.assertEqual(self.manager.unmapped, {})

    async def test_creation_rollback_failure_preserves_ownership_for_cleanup_retry(self):
        for action in ('delete', 'force'):
            with self.subTest(action=action):
                project_id = 'rollback-' + action
                with patch.object(self.keti2_sources, 'search', return_value=[item(self.source)]), \
                     patch.object(self.manager.store, 'add', side_effect=sqlite3.OperationalError('映射写入失败')), \
                     patch.object(Task, 'delete_files', side_effect=PermissionError('回滚失败')):
                    await self.manager.submit(project_id)
                    await self.manager.jobs[('keti2', project_id)]
                progress = self.manager.progress(project_id, source='keti2')
                self.assertEqual(progress['status'], 'failed')
                self.assertEqual(progress['total'], 1)
                task = progress['tasks'][0]
                self.assertEqual((task['status'], task['chatstatus']), ('cancelled', 'cancelled'))
                task_id = task['task_id']
                self.assertIn(task_id, self.tasks.tasks)
                with patch.object(self.tasks, 'delete_task', side_effect=PermissionError('仍无法删除')):
                    with self.assertRaises(PermissionError):
                        await self.manager.delete(project_id, source='keti2')
                self.assertEqual(self.manager.progress(project_id, source='keti2')['total'], 1)
                with patch.object(self.keti2_sources, 'search', return_value=[]):
                    if action == 'delete':
                        await self.manager.delete(project_id, source='keti2')
                    else:
                        await self.manager.submit(project_id, force=True)
                        await self.manager.jobs[('keti2', project_id)]
                self.assertNotIn(project_id, self.manager.unmapped)
                self.assertNotIn(task_id, self.tasks.tasks)
                self.assertFalse((config.VIP_TASK_DIR / task_id).exists())

    async def test_mark_unfinished_synchronizes_only_active_metadata(self):
        task_id = self.manager._create(('keti2', 'unfinished'), None, 'B_State')
        path = config.VIP_TASK_DIR / task_id / 'task.json'
        original = json.loads(path.read_text())
        for active in ('created', 'queued', 'running'):
            for verification in (None, 'created', 'queued', 'running', 'completed', 'failed'):
                with self.subTest(active=active, verification=verification):
                    metadata = {**original, 'status': active, 'chatstatus': active}
                    if verification is not None:
                        metadata['verification_status'] = verification
                    _write_metadata(path, metadata)
                    self.manager._mark_unfinished(task_id, 'failed')
                    updated = json.loads(path.read_text())
                    self.assertEqual(updated['status'], 'failed')
                    self.assertEqual(updated['chatstatus'], 'failed')
                    self.assertEqual(updated['verification_status'],
                                     verification if verification in ('completed', 'failed') else 'failed')
        for terminal in ('completed', 'failed', 'cancelled', 'idle', 'paused'):
            metadata = {**original, 'status': terminal, 'chatstatus': terminal,
                        'verification_status': 'completed'}
            _write_metadata(path, metadata)
            self.manager._mark_unfinished(task_id)
            self.assertEqual(json.loads(path.read_text()), metadata)

    async def test_id_collision_retry(self):
        # 同日随机部分碰撞时重新取随机值，数据库和目录均不覆盖。
        with patch('app.vip_task.inputs.secrets.choice', side_effect=list('aaaaaaaabbbb')):
            first = self.manager._create(('keti2', 'ids'), None, 'B_Ids')
            second = self.manager._create(('keti2', 'ids'), None, 'B_Ids')
        self.assertNotEqual(first, second)
        self.assertTrue(first.endswith('aaaa'))
        self.assertTrue(second.endswith('bbbb'))


class ApiTests(unittest.TestCase):
    def test_routes_validation_results_and_download(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'code.c'
            source.write_text('code')
            async def fake_run(task):
                output = task.task_dir / 'workspace' / 'output'
                output.mkdir()
                (output / 'result.txt').write_text('verified')
                status(task, 'completed')
            with patch.object(config, 'VIP_TASK_DIR', root / 'tasks'), \
                 patch.dict('os.environ', {'VIP_PROJECT_DB': str(root / 'map.sqlite3')}), \
                 patch.object(Keti2Sources, 'search', return_value=[item(source)]), \
                 patch.object(Task, 'run', fake_run), TestClient(create_app(backend_only=True)) as client:
                self.assertEqual(client.get('/project/get_progress', params={'source': 'keti2', 'projectID': 'unknown'}).status_code, 404)
                self.assertEqual(client.post('/project/create_project', json={'source': 'keti2', 'projectID': ''}).status_code, 422)
                response = client.post('/project/create_project', json={'source': 'keti2', 'projectID': 'p'})
                self.assertEqual(response.status_code, 202)
                self.assertEqual(response.json(), {'projectID': 'p', 'keti': 'keti2', 'status': 'accepted'})
                self.assertEqual(client.post('/project/create_project', json={'source': 'keti2', 'projectID': 'p'}).status_code, 409)
                import time
                for _ in range(100):
                    progress = client.get('/project/get_progress', params={'source': 'keti2', 'projectID': 'p'}).json()
                    if progress['status'] == 'completed':
                        break
                    time.sleep(.005)
                self.assertEqual(progress['status'], 'completed')
                self.assertEqual(progress['tasks'][0]['ip_id'], 'B_TcProcess')
                listing = client.get('/task/list_tasks')
                self.assertEqual(listing.status_code, 200)
                self.assertEqual(len(listing.json()['tasks']), 1)
                result = client.get('/project/get_results', params={'source': 'keti2', 'projectID': 'p'}).json()
                self.assertEqual(result['tasks'][0]['ip_id'], 'B_TcProcess')
                url = result['tasks'][0]['files'][0]['download_url']
                self.assertEqual(client.get(url).text, 'verified')
                task_id = result['tasks'][0]['task_id']
                self.assertEqual(client.delete('/task/delete_task', params={'task_id': task_id}).status_code, 200)
                response = client.post('/task/create_task', json={'task_id': task_id, 'prompt': '人工任务'})
                self.assertEqual(response.status_code, 422)
                self.assertEqual(client.get('/task/list_tasks', params={'task_id': task_id}).json()['tasks'], [])
                forced = client.post('/project/create_project', json={'source': 'keti2', 'projectID': 'p', 'force': True})
                self.assertEqual(forced.status_code, 202)
                self.assertEqual(forced.json(), {'projectID': 'p', 'keti': 'keti2', 'status': 'accepted'})
                for _ in range(100):
                    progress = client.get('/project/get_progress', params={'source': 'keti2', 'projectID': 'p'}).json()
                    if progress['status'] == 'completed':
                        break
                    time.sleep(.005)
                self.assertEqual(progress['status'], 'completed')
                self.assertEqual(len(progress['tasks']), 1)
                self.assertNotEqual(progress['tasks'][0]['task_id'], task_id)
                self.assertEqual(client.get('/task/get_task', params={'task_id': task_id}).status_code, 404)

                self.assertEqual(client.post('/project/create_project', json={'source': 'keti2', 'projectID': 'p', 'source': 'invalid'}).status_code, 422)
                self.assertEqual(client.post('/project/delete_project', json={'source': 'keti2', 'projectID': ' '}).status_code, 422)
                self.assertEqual(client.post('/project/delete_project', json={'source': 'keti2', 'projectID': 'unknown'}).status_code, 404)
                manager = client.app.state.project_manager
                with patch.object(manager, 'submit', new_callable=AsyncMock, return_value={'status': 'accepted'}) as submit:
                    response = client.post('/project/create_project', json={
                        'projectID': '123', 'source': 'keti3', 'userprompt': '验证要求', 'force': True})
                    self.assertEqual(response.status_code, 202)
                    submit.assert_awaited_once_with('123', '验证要求', force=True, source='keti3', tool='CBMC')
                    for source in ('keti2', 'keti3'):
                        for tool in ('CBMC', 'CPAchecker', 'KLEE'):
                            submit.reset_mock()
                            response = client.post('/project/create_project', json={
                                'projectID': '123', 'source': source, 'tool': tool, 'force': True})
                            self.assertEqual(response.status_code, 202)
                            submit.assert_awaited_once_with('123', None, force=True, source=source, tool=tool)
                    for tool in ('unknown', '', None):
                        submit.reset_mock()
                        self.assertEqual(client.post('/project/create_project', json={
                            'projectID': '123', 'tool': tool, 'force': True}).status_code, 422)
                        submit.assert_not_called()
                with patch.object(manager, 'delete', side_effect=ProjectConflictError('项目正在清理')):
                    self.assertEqual(client.post('/project/delete_project', json={'source': 'keti2', 'projectID': 'p'}).status_code, 409)
                for error, code in ((PermissionError('无权删除'), 403), (OSError('删除失败'), 500)):
                    with patch.object(manager.task_manager, 'delete_task', side_effect=error):
                        self.assertEqual(client.post('/project/delete_project', json={'source': 'keti2', 'projectID': 'p'}).status_code, code)
                    self.assertEqual(client.get('/project/get_progress', params={'source': 'keti2', 'projectID': 'p'}).json()['status'], 'failed')
                response = client.post('/project/delete_project', json={'source': 'keti2', 'projectID': 'p'})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {'projectID': 'p', 'keti': 'keti2', 'status': 'deleted'})
                self.assertEqual(client.get('/project/get_progress', params={'source': 'keti2', 'projectID': 'p'}).status_code, 404)
                self.assertEqual(client.get('/project/get_results', params={'source': 'keti2', 'projectID': 'p'}).status_code, 404)
                self.assertEqual(client.post('/project/delete_project', json={'source': 'keti2', 'projectID': 'p'}).status_code, 404)
                self.assertEqual(client.get('/task/list_tasks').json()['tasks'], [])
                self.assertEqual(client.get('/api/project/get_progress', params={'source': 'keti2', 'projectID': 'p'}).status_code, 404)


if __name__ == '__main__':
    unittest.main()
