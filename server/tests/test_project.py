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
from app.vip_task.project import ProjectManager, ProjectStore, ProjectNotFoundError
from app.vip_task.task import Task, TaskConflictError, _write_metadata
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
    def test_old_schema_migration_preserves_rows_and_adds_missing_fields(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'mapping.sqlite3'
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE project_tasks (task_id TEXT PRIMARY KEY, projectID TEXT NOT NULL)')
                db.execute("INSERT INTO project_tasks VALUES ('old', 'project')")
            store = ProjectStore(path)
            try:
                self.assertEqual(store.entries('project'), [{'task_id': 'old', 'ip_id': '', 'timestamp': '2026-10-14 00:00:00'}])
                store.add('new', 'project', 'B_TcProcess', timestamp='2026-10-14 12:00:00.123456')
                columns = {row[1] for row in store.db.execute('PRAGMA table_info(project_tasks)')}
                self.assertEqual(columns, {'task_id', 'projectID', 'ip_id', 'keti', 'timestamp'})
            finally:
                store.close()
            restored = ProjectStore(path)
            try:
                self.assertEqual(restored.entries('project'), [
                    {'task_id': 'old', 'ip_id': '', 'timestamp': '2026-10-14 00:00:00'},
                    {'task_id': 'new', 'ip_id': 'B_TcProcess', 'timestamp': '2026-10-14 12:00:00.123456'}])
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
            await self.manager.jobs[batch_key(self.manager, 'keti2', '项目')]
        progress = self.manager.progress('项目', source='keti2')
        self.assertEqual((progress['status'], progress['total'], progress['finished']), ('completed', 2, 2))
        self.assertEqual(started, self.manager.store.tasks('项目', keti='keti2'))
        self.assertEqual([t['ip_id'] for t in progress['tasks']], ['B_First', 'B_Second'])
        self.assertTrue(all(len(i) == 8 and i[:4].isdigit() and i[4:].isalnum() for i in started))
        result = self.manager.results('项目', source='keti2')
        self.assertEqual([t['ip_id'] for t in result['tasks']], ['B_First', 'B_Second'])
        self.assertEqual(len(result['tasks'][0]['files']), 1)
        self.assertTrue(result['tasks'][0]['files'][0]['download_url'].startswith('/task/get_file?'))
        restored = ProjectManager(self.tasks, ProjectStore(self.root / 'mapping.sqlite3'), self.keti2_sources)
        try:
            self.assertEqual(restored.progress('项目', source='keti2')['status'], 'completed')
            self.assertEqual([t['ip_id'] for t in restored.progress('项目', source='keti2')['tasks']], ['B_First', 'B_Second'])
            self.assertEqual(restored.results('项目', source='keti2'), result)
            accepted = await restored.submit('项目')
            self.assertIn('timestamp', accepted)
        finally:
            await restored.close()

    async def test_concurrent_same_project_has_isolated_batches_and_single_task_delete(self):
        entered = asyncio.Event()
        started = []
        async def fake_run(task):
            started.append(task.task_id)
            if len(started) == 1:
                status(task, 'running')
                entered.set()
                await asyncio.Event().wait()
            status(task, 'completed')
        with patch.object(self.keti2_sources, 'search', return_value=[item(self.source), item(self.source)]) as search, \
             patch.object(Task, 'run', fake_run):
            accepted = await asyncio.gather(self.manager.submit('same'), self.manager.submit('same'))
            timestamps = [batch['timestamp'] for batch in accepted]
            self.assertEqual(len(set(timestamps)), 2)
            self.assertTrue(all(len(timestamp) == 26 for timestamp in timestamps))
            await asyncio.wait_for(entered.wait(), 5)
            for _ in range(500):
                progress = self.manager.progress('same', source='keti2')
                if progress['total'] == 4:
                    break
                await asyncio.sleep(.01)
            self.assertEqual(progress['total'], 4)
            self.assertEqual(len(self.manager.jobs), 2)
            self.assertEqual(len(progress['batches']), 2)
            for batch in progress['batches']:
                self.assertEqual(batch['total'], 2)
                for task in batch['tasks']:
                    self.assertEqual(task['timestamp'], batch['timestamp'])
                    self.assertEqual(Task._metadata(config.VIP_TASK_DIR / task['task_id'])['timestamp'], batch['timestamp'])
            # 删除首批正在运行的任务，两个编排都继续，不取消其他批次。
            victim = started[0]
            victim_timestamp = Task._metadata(config.VIP_TASK_DIR / victim)['timestamp']
            await self.tasks.delete_task(victim)
            await asyncio.wait_for(asyncio.gather(*self.manager.jobs.values()), 5)
        self.assertEqual(search.call_args_list, [unittest.mock.call('same'), unittest.mock.call('same')])
        progress = self.manager.progress('same', source='keti2')
        self.assertEqual(progress['total'], 3)
        self.assertEqual(progress['finished'], 3)
        self.assertEqual(len(started), 4)
        self.assertTrue(all(task['status'] == 'completed' for task in progress['tasks']))
        self.assertEqual([batch['total'] for batch in progress['batches'] if batch['timestamp'] != victim_timestamp], [2])
        result = self.manager.results('same', source='keti2')
        self.assertEqual({task['timestamp'] for task in result['tasks']}, set(timestamps))
        self.assertEqual(len(result['batches']), 2)
        listing = self.tasks.list_tasks(projectID='same')['tasks']
        self.assertEqual({task['timestamp'] for task in listing}, set(timestamps))

    async def test_missing_or_nonstring_business_id_does_not_block_tasks(self):
        values = [item(self.source, ip_id=None), item(self.source, ip_id=345), item(self.source)]
        del values[2]['ipMsg']['entity']['basicInformation']
        async def fake_run(task):
            status(task, 'completed')
        with patch.object(self.keti2_sources, 'search', return_value=values), patch.object(Task, 'run', fake_run):
            await self.manager.submit('missing-id')
            await self.manager.jobs[batch_key(self.manager, 'keti2', 'missing-id')]
        progress = self.manager.progress('missing-id', source='keti2')
        self.assertEqual(progress['status'], 'completed')
        self.assertEqual([task['ip_id'] for task in progress['tasks']], ['', '', ''])

    async def test_collecting_without_fake_tasks_and_created_downloading(self):
        searched, collecting, release_search, release_collect = (threading.Event() for _ in range(4))
        def search(project_id):
            searched.set()
            release_search.wait(3)
            return [item(self.source)]
        def collect(*args):
            collecting.set()
            release_collect.wait(3)
            raise OSError('raw download error')
        with patch.object(self.keti2_sources, 'search', search), patch.object(self.keti2_sources, 'collect', collect):
            accepted = await self.manager.submit('pending')
            try:
                self.assertTrue(await asyncio.to_thread(searched.wait, 3))
                batch = self.manager.progress('pending', source='keti2')['batches'][0]
                self.assertEqual(batch['timestamp'], accepted['timestamp'])
                self.assertEqual(batch['status'], 'collecting')
                self.assertEqual(batch['tasks'], [])
                self.assertEqual(self.tasks.list_tasks()['tasks'], [])
                release_search.set()
                self.assertTrue(await asyncio.to_thread(collecting.wait, 3))
                row = self.tasks.list_tasks()['tasks'][0]
                self.assertEqual(row['status'], 'created')
                self.assertEqual(row['preparation_status'], 'downloading')
                with self.assertRaises(TaskConflictError):
                    await self.tasks.run_task(row['task_id'])
            finally:
                release_search.set()
                release_collect.set()
                await self.manager.jobs[batch_key(self.manager, 'keti2', 'pending')]
        row = self.tasks.list_tasks()['tasks'][0]
        self.assertEqual(row['status'], 'failed')
        self.assertEqual(row['preparation_error'], '文件下载失败：raw download error')

    async def test_empty_and_network_failure(self):
        with patch.object(self.keti2_sources, 'search', return_value=[]):
            await self.manager.submit('empty')
            await self.manager.jobs[batch_key(self.manager, 'keti2', 'empty')]
        self.assertEqual({key: value for key, value in self.manager.progress('empty', source='keti2').items() if key != 'batches'}, {
            'projectID': 'empty', 'keti': 'keti2', 'status': 'empty', 'source': 'keti2', 'total': 0, 'finished': 0, 'tasks': []})
        with patch.object(self.keti2_sources, 'search', side_effect=OSError('network failed')):
            await self.manager.submit('bad')
            await self.manager.jobs[batch_key(self.manager, 'keti2', 'bad')]
        self.assertEqual(self.manager.progress('bad', source='keti2')['error'], '项目输入查询或打包失败：network failed')

    async def test_keti3_pack_failure_and_empty_have_timestamp_without_tasks(self):
        with patch.object(self.manager.keti3_sources, 'search', side_effect=OSError('pack rejected')):
            first = await self.manager.submit('7', source='keti3')
            await self.manager.jobs[('keti3', '7', first['timestamp'])]
        with patch.object(self.manager.keti3_sources, 'search', return_value=[]):
            second = await self.manager.submit('7', source='keti3')
            await self.manager.jobs[('keti3', '7', second['timestamp'])]
        batches = self.manager.progress('7', source='keti3')['batches']
        self.assertEqual([batch['timestamp'] for batch in batches], [first['timestamp'], second['timestamp']])
        self.assertEqual([batch['status'] for batch in batches], ['failed', 'empty'])
        self.assertIn('项目输入查询或打包失败：pack rejected', batches[0]['error'])
        self.assertEqual([batch['tasks'] for batch in batches], [[], []])
        self.assertEqual(self.tasks.list_tasks()['tasks'], [])

    async def test_collection_failure_does_not_skip_other_ips(self):
        async def fake_run(task):
            status(task, 'completed')
        with patch.object(self.keti2_sources, 'search', return_value=[item('/missing/a.c'), item(self.source)]), \
             patch.object(Task, 'run', fake_run):
            await self.manager.submit('broken')
            await self.manager.jobs[batch_key(self.manager, 'keti2', 'broken')]
        progress = self.manager.progress('broken', source='keti2')
        self.assertEqual(progress['status'], 'failed')
        self.assertEqual(progress['total'], 2)
        self.assertEqual([t['status'] for t in progress['tasks']], ['failed', 'completed'])
        failed, ready = progress['tasks']
        self.assertEqual(failed['preparation_status'], 'failed')
        self.assertIn('文件下载失败：', failed['preparation_error'])
        self.assertEqual(ready['preparation_status'], 'ready')
        rows = {row['task_id']: row for row in self.tasks.list_tasks()['tasks']}
        self.assertEqual(rows[failed['task_id']]['preparation_error'], failed['preparation_error'])
        for control in (self.tasks.run_task, self.tasks.pause_task):
            with self.assertRaises(TaskConflictError):
                await control(failed['task_id'])
        with self.assertRaises(TaskConflictError):
            await self.tasks.send_message(failed['task_id'], '不能使用缺失输入启动 Pi')
        self.assertEqual(self.tasks.get_task(failed['task_id'])['task']['preparation_error'], failed['preparation_error'])

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
            job = self.manager.jobs[batch_key(self.manager, 'keti2', 'shutdown')]
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
            await self.manager.jobs[batch_key(self.manager, 'keti2', 'delete-one')]
        progress = self.manager.progress('delete-one', source='keti2')
        self.assertEqual(len(started), 2)
        self.assertEqual(progress['status'], 'completed')
        self.assertEqual(len(progress['tasks']), 1)
        self.assertEqual(progress['tasks'][0]['status'], 'completed')
        self.assertFalse(self.manager.store.has_task(started[0]))

    async def test_progress_does_not_scan_workspace(self):
        with patch.object(self.keti2_sources, 'search', return_value=[item(self.source)]):
            await self.manager.submit('metadata-only')
            self.manager.jobs[batch_key(self.manager, 'keti2', 'metadata-only')].cancel()
            await asyncio.gather(self.manager.jobs[batch_key(self.manager, 'keti2', 'metadata-only')], return_exceptions=True)
        self.manager._create(('keti2', 'metadata-only', '2026-10-14 00:00:00'), None, 'B_Meta')
        with patch.object(self.tasks, 'get_task', side_effect=AssertionError('不应扫描 workspace')):
            self.assertEqual(self.manager.progress('metadata-only', source='keti2')['total'], 1)

    async def test_chat_status_does_not_overwrite_project_verification(self):
        task_id = self.manager._create(('keti2', 'chat-project', '2026-10-14 00:00:00'), None, 'B_Chat')
        path = config.VIP_TASK_DIR / task_id / 'task.json'
        metadata = json.loads(path.read_text())
        metadata.update(status='idle', chatstatus='idle', verification_status='completed')
        _write_metadata(path, metadata)
        self.manager.projects[('keti2', 'chat-project', '2026-10-14 00:00:00')] = {'status': 'completed'}
        task = self.manager.progress('chat-project', source='keti2')['tasks'][0]
        self.assertEqual(task['status'], 'completed')
        self.assertEqual(task['chatstatus'], 'idle')
        self.assertEqual(self.manager.progress('chat-project', source='keti2')['finished'], 1)
        self.manager.projects[('keti2', 'chat-project', '2026-10-14 00:00:00')] = {'status': 'failed', 'error': '旧任务未完成'}
        progress = self.manager.progress('chat-project', source='keti2')
        self.assertEqual(progress['status'], 'completed')
        self.assertNotIn('error', progress)






    async def test_partial_creation_failure_cannot_be_reported_as_completed(self):
        async def fake_run(task):
            status(task, 'completed')
        create = self.manager._create
        def failing_create(project_id, prompt, ip_id, ip_name, tool):
            if ip_id == 'B_Broken':
                raise OSError('无法创建任务')
            return create(project_id, prompt, ip_id, ip_name, tool)
        with patch.object(self.keti2_sources, 'search', return_value=[item(self.source, ip_id='B_Broken'), item(self.source, ip_id='B_Good')]), patch.object(self.manager, '_create', failing_create), patch.object(Task, 'run', fake_run):
            await self.manager.submit('partial-create')
            await self.manager.jobs[batch_key(self.manager, 'keti2', 'partial-create')]
        progress = self.manager.progress('partial-create', source='keti2')
        self.assertEqual(progress['status'], 'failed')
        self.assertIn('创建失败', progress['error'])
        self.assertEqual(progress['tasks'][0]['status'], 'completed')
        self.assertNotIn('requires_resubmit', progress)








    async def test_project_finalization_does_not_cancel_a_new_chat_job(self):
        task_id = self.manager._create(('keti2', 'chat-race', '2026-10-14 00:00:00'), None, 'B_Chat')
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


    async def test_store_add_failure_rolls_back_unstarted_task(self):
        with patch.object(self.manager.store, 'add', side_effect=sqlite3.OperationalError('映射写入失败')), \
             patch.object(Task, 'run', side_effect=AssertionError('不应启动 Pi')):
            with self.assertRaises(sqlite3.OperationalError):
                self.manager._create(('keti2', 'rollback', '2026-10-14 00:00:00'), None, 'B_Rollback')
        self.assertEqual(self.manager.store.tasks('rollback', keti='keti2'), [])
        self.assertEqual(self.tasks.tasks, {})
        self.assertEqual(list(config.VIP_TASK_DIR.iterdir()), [])
        self.assertEqual(self.manager.unmapped, {})

    async def test_creation_rollback_failure_preserves_ownership_for_task_delete(self):
        with patch.object(self.keti2_sources, 'search', return_value=[item(self.source)]), \
             patch.object(self.manager.store, 'add', side_effect=sqlite3.OperationalError('映射写入失败')), \
             patch.object(Task, 'delete_files', side_effect=PermissionError('回滚失败')):
            accepted = await self.manager.submit('rollback')
            await self.manager.jobs[('keti2', 'rollback', accepted['timestamp'])]
        progress = self.manager.progress('rollback', source='keti2')
        self.assertEqual(progress['status'], 'failed')
        self.assertEqual(progress['total'], 1)
        task_id = progress['tasks'][0]['task_id']
        self.assertEqual(progress['tasks'][0]['timestamp'], accepted['timestamp'])
        await self.tasks.delete_task(task_id)
        self.assertEqual(self.manager.progress('rollback', source='keti2')['total'], 0)
        self.assertFalse((config.VIP_TASK_DIR / task_id).exists())

    async def test_mark_unfinished_synchronizes_only_active_metadata(self):
        task_id = self.manager._create(('keti2', 'unfinished', '2026-10-14 00:00:00'), None, 'B_State')
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
            first = self.manager._create(('keti2', 'ids', '2026-10-14 00:00:00'), None, 'B_Ids')
            second = self.manager._create(('keti2', 'ids', '2026-10-14 00:00:00'), None, 'B_Ids')
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
                self.assertEqual({key: value for key, value in response.json().items() if key != 'timestamp'},
                                 {'projectID': 'p', 'keti': 'keti2', 'status': 'accepted'})
                self.assertIn('timestamp', response.json())
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
                repeated = client.post('/project/create_project', json={'source': 'keti2', 'projectID': 'p'})
                self.assertEqual(repeated.status_code, 202)
                self.assertEqual(repeated.json()['status'], 'accepted')
                self.assertRegex(repeated.json()['timestamp'], r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}$')
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
                self.assertEqual(client.post('/project/delete_project', json={'source': 'keti2', 'projectID': 'p'}).status_code, 404)
                self.assertEqual(client.post('/project/delete_project', json={'source': 'keti2', 'projectID': 'unknown'}).status_code, 404)
                manager = client.app.state.project_manager
                with patch.object(manager, 'submit', new_callable=AsyncMock, return_value={'status': 'accepted'}) as submit:
                    response = client.post('/project/create_project', json={
                        'projectID': '123', 'source': 'keti3', 'userprompt': '验证要求'})
                    self.assertEqual(response.status_code, 202)
                    submit.assert_awaited_once_with('123', '验证要求', source='keti3', tool='CBMC')
                    for source in ('keti2', 'keti3'):
                        for tool in ('CBMC', 'CPAchecker', 'KLEE'):
                            submit.reset_mock()
                            response = client.post('/project/create_project', json={
                                'projectID': '123', 'source': source, 'tool': tool})
                            self.assertEqual(response.status_code, 202)
                            submit.assert_awaited_once_with('123', None, source=source, tool=tool)
                    for tool in ('unknown', '', None):
                        submit.reset_mock()
                        self.assertEqual(client.post('/project/create_project', json={
                            'projectID': '123', 'tool': tool}).status_code, 422)
                        submit.assert_not_called()



def batch_key(manager, source, project_id):
    return next(key for key in reversed(manager.jobs) if key[:2] == (source, project_id))


if __name__ == '__main__':
    unittest.main()
