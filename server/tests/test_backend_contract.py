"""新接口契约与来源隔离测试；全部数据位于临时目录。"""
import asyncio
import json
import os
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.vip_task import config
from app.vip_task.archive import task_archive
from app.vip_task.inputs import create_local, create_registered
from app.vip_task.project import ProjectManager, ProjectStore, ProjectNotFoundError
from app.vip_task.task import Task, TaskPathError, _write_metadata
from app.vip_task.task_manager import TaskManager
from main import create_app


class BackendTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patch = patch.object(config, 'VIP_TASK_DIR', self.root / 'tasks')
        self.patch.start()
        self.tasks = TaskManager()
        self.store = ProjectStore(self.root / 'test.db')
        self.sources = Mock()
        self.sources.search.return_value = []
        self.manager = ProjectManager(self.tasks, self.store, self.sources, self.sources)

    async def asyncTearDown(self):
        await self.manager.close()
        await self.tasks.close()
        self.patch.stop()
        self.temp.cleanup()

    async def test_source_isolation_force_delete_and_historical_null(self):
        historic = create_registered(self.tasks, self.store, '历史', 'CBMC', None, project_id='1001')['task_id']
        k2 = self.manager._create(('keti2', '1001'), '用户', 'id2', '名称2')
        k3 = self.manager._create(('keti3', '1001'), '用户', 'id3', '名称3')
        self.assertEqual(self.manager.progress('1001', source='keti2')['total'], 1)
        self.assertEqual(self.manager.progress('1001', source='keti3')['tasks'][0]['ip_name'], '名称3')
        await self.manager.submit('1001', source='keti2', force=True)
        await self.manager.jobs[('keti2', '1001')]
        self.assertFalse(self.store.has_task(k2))
        self.assertTrue(self.store.has_task(k3))
        self.assertTrue(self.store.has_task(historic))
        await self.manager.delete('1001', source='keti3')
        self.assertTrue(self.store.has_task(historic))
        with self.assertRaises(ProjectNotFoundError):
            self.manager.progress('1001', source='keti3')
        await self.tasks.delete_task(historic)
        self.assertFalse(self.store.has_task(historic))

    async def test_remote_tools_reach_execution_and_force_preserves_selection(self):
        self.sources.search.return_value = [{'ipId': 'one'}]
        seen = []
        async def run(task):
            metadata = Task._metadata(task.task_dir)
            tool = metadata['tool']
            self.assertIn(f'使用 {tool} 验证软件 IP', task.prompt)
            seen.append(tool)
            metadata.update(status='completed', verification_status='completed')
            _write_metadata(task.task_dir / 'task.json', metadata)
        with patch.object(Task, 'run', run):
            for source in ('keti2', 'keti3'):
                for tool in ('CBMC', 'CPAchecker', 'KLEE'):
                    await self.manager.submit('123', source=source, tool=tool, force=True)
                    await self.manager.jobs[(source, '123')]
                    self.assertEqual(self.manager.progress('123', source=source)['status'], 'completed')
        self.assertEqual(seen, ['CBMC', 'CPAchecker', 'KLEE'] * 2)
        old = self.store.tasks('123', 'keti2')
        with self.assertRaises(ValueError):
            await self.manager.submit('123', source='keti2', tool='bad', force=True)
        self.assertEqual(self.store.tasks('123', 'keti2'), old)

    async def test_prompt_user_segment_and_names_only_in_metadata(self):
        for source in (None, 'keti2', 'keti3'):
            result = create_registered(self.tasks, self.store, '名字', 'CPAchecker', '指定要求', keti=source)
            task = self.tasks.tasks[result['task_id']]
            before, user = task.prompt.split('<userpropmt>')
            self.assertIn('以 userpropmt 为准', before)
            self.assertEqual(user, '\n指定要求\n</userpropmt>')
            self.assertEqual(Task._metadata(task.task_dir)['ip_name'], '名字')
        self.assertEqual({r[1] for r in self.store.db.execute('PRAGMA table_info(project_tasks)')},
                         {'task_id', 'projectID', 'keti', 'ip_id'})

    async def test_task_id_placeholder_uses_final_id_after_collision(self):
        date = __import__('datetime').datetime.now().strftime('%m%d')
        self.store.add(date + 'aaaa', None, '')
        prompt = ('输入 /app/vip4/tasks/<task_id>/input/ip/AttiCal；'
                  '输出 /app/vip4/tasks/<task_id>/workspace/cbmc_suite/output')
        for source in (None, 'keti2', 'keti3'):
            with patch('app.vip_task.inputs.secrets.choice', side_effect=list('aaaabbbbccccdddd')):
                result = create_registered(self.tasks, self.store, 'AttiCal', 'CBMC', prompt, keti=source)
            task_id = result['task_id']
            actual = self.tasks.tasks[task_id].prompt
            self.assertNotIn('<task_id>', actual)
            self.assertIn(f'/app/vip4/tasks/{task_id}/input/ip/AttiCal', actual)
            self.assertIn(f'/app/vip4/tasks/{task_id}/workspace/cbmc_suite/output', actual)
            self.assertTrue(actual.endswith('<userpropmt>\n' + prompt.replace('<task_id>', task_id) + '\n</userpropmt>'))

    async def test_null_ip_information_does_not_skip_valid_items(self):
        values = [None, {}, {'entity': None}, {'entity': {}},
                  {'entity': {'basicInformation': None}},
                  {'entity': {'basicInformation': {}}},
                  {'entity': {'basicInformation': {'id': None, 'name': None}}},
                  {'entity': {'basicInformation': {'id': 'only-id'}}},
                  {'entity': {'basicInformation': {'id': 12, 'name': ['非法名称']}}}]
        items = [{'ipId': str(index), 'ipMsg': value} for index, value in enumerate(values)]
        self.sources.search.return_value = items
        async def run(task):
            task.set_status('completed')
        with patch.object(Task, 'run', run):
            await self.manager.submit('null-info')
            await self.manager.jobs[('keti2', 'null-info')]
        self.assertEqual(self.sources.collect.call_count, len(items))
        progress = self.manager.progress('null-info', source='keti2')
        self.assertEqual(progress['status'], 'completed')
        self.assertEqual(progress['total'], len(items))
        self.assertEqual([task['ip_name'] for task in progress['tasks']], [''] * len(items))
        self.assertEqual([task['ip_id'] for task in progress['tasks']], [''] * 7 + ['only-id', ''])

    async def test_zip_stream_supports_zip64_without_known_size(self):
        task_id = self.manager._create(('keti2', 'zip64'), None, 'id')
        contents = b'large-file' * 100
        (config.VIP_TASK_DIR / task_id / 'workspace/large.bin').write_bytes(contents)
        # 降低阈值模拟超过 2 GiB 的文件，不创建实际大文件。
        with patch.object(zipfile, 'ZIP64_LIMIT', 128):
            archive = task_archive(task_id)
        try:
            with zipfile.ZipFile(archive) as zipped:
                self.assertEqual(zipped.read(task_id + '/workspace/large.bin'), contents)
                self.assertGreaterEqual(zipped.getinfo(task_id + '/workspace/large.bin').extract_version, 45)
        finally:
            archive.unlink()

    async def test_list_missing_and_legacy_directory_filters(self):
        deleted = self.manager._create(('keti2', 'p'), None, 'id', '名称')
        self.tasks.tasks[deleted].delete_files()
        broken = self.manager._create(('keti3', 'p'), None, 'id', '名称')
        (config.VIP_TASK_DIR / broken / 'task.json').unlink()
        self.tasks.create_task('legacy', '历史手动', start=False)
        rows = {r['task_id']: r for r in self.tasks.list_tasks()['tasks']}
        self.assertTrue(rows[deleted]['directory_missing'])
        self.assertTrue(rows[broken]['data_missing'])
        self.assertFalse(rows[broken]['directory_missing'])
        self.assertIsNone(rows['legacy']['keti'])
        self.assertEqual(len(self.tasks.list_tasks('p')['tasks']), 2)
        self.assertEqual(self.tasks.list_tasks('p', deleted, 'keti3')['tasks'], [])
        self.assertEqual(len(self.tasks.list_tasks('p', deleted, 'keti2')['tasks']), 1)
        (config.VIP_TASK_DIR / 'legacy/workspace').rmdir()
        self.assertTrue(self.tasks.list_tasks(task_id='legacy')['tasks'][0]['data_missing'])
        self.assertTrue(self.store.has_task(deleted))
        await self.tasks.delete_task(deleted)
        self.assertFalse(self.store.has_task(deleted))
        # 破损数据也可显式永久删除。
        await self.tasks.delete_task(broken)
        self.assertFalse(self.store.has_task(broken))

    async def test_local_copy_complete_layout_and_all_tools(self):
        data = self.root / 'dataset'
        (data / 'ip' / 'Demo' / 'nested').mkdir(parents=True)
        (data / 'include' / 'nested').mkdir(parents=True)
        (data / 'ip' / 'Demo' / 'nested' / 'model.txt').write_bytes(b'model')
        (data / 'include' / 'nested' / 'head.h').write_bytes(b'header')
        async def run(task):
            metadata = Task._metadata(task.task_dir)
            metadata.update(status='completed')
            _write_metadata(task.task_dir / 'task.json', metadata)
        with patch.object(config, 'VIP_DATASET_DIR', data), patch.object(Task, 'run', run):
            for tool in ('CBMC', 'CPAchecker', 'KLEE'):
                result = await create_local(self.tasks, self.store, 'Demo', tool, '')
                task = self.tasks.tasks[result['task_id']]
                await task.job
                self.assertTrue((task.task_dir / 'input/ip/Demo/nested/model.txt').is_file())
                self.assertTrue((task.task_dir / 'input/include/nested/head.h').is_file())
                row = self.tasks.list_tasks(task_id=task.task_id)['tasks'][0]
                self.assertIsNone(row['projectID'])
                self.assertIsNone(row['keti'])
                self.assertIn(tool, task.prompt)
                with self.assertRaises(ValueError):
                    await create_local(self.tasks, self.store, '../escape', tool, '')

    async def test_id_collision_database_directory_and_insert_race(self):
        # 先撞DB再撞目录，最后分配成功。
        date = __import__('datetime').datetime.now().strftime('%m%d')
        self.store.add(date + 'aaaa', None, '')
        self.tasks.create_task(date + 'bbbb', '手动', start=False)
        with patch('app.vip_task.inputs.secrets.choice', side_effect=list('aaaabbbbcccc')):
            task_id = self.manager._create(('keti2', 'p'), None, 'id')
        self.assertEqual(task_id, date + 'cccc')
        add = self.store.add
        def racing(task_id, *args):
            if task_id.endswith('dddd'):
                add(task_id, None, '')
                raise sqlite3.IntegrityError('UNIQUE constraint failed')
            return add(task_id, *args)
        with patch.object(self.store, 'add', racing), patch('app.vip_task.inputs.secrets.choice', side_effect=list('ddddeeee')):
            task_id = self.manager._create(('keti2', 'p'), None, 'id')
        self.assertEqual(task_id, date + 'eeee')
        self.assertFalse((config.VIP_TASK_DIR / (date + 'dddd')).exists())

    async def test_zip_complete_and_reject_unsafe_files(self):
        task_id = self.manager._create(('keti2', 'p'), None, 'id')
        directory = config.VIP_TASK_DIR / task_id
        for name in ('input/a.c', 'pi_session/context.json', 'workspace/result.txt', 'files.csv'):
            (directory / name).write_bytes(name.encode())
        archive = task_archive(task_id)
        try:
            with zipfile.ZipFile(archive) as zipped:
                for name in ('input/a.c', 'pi_session/context.json', 'workspace/result.txt', 'files.csv', 'task.json'):
                    self.assertIn(task_id + '/' + name, zipped.namelist())
        finally:
            archive.unlink()
        external = self.root / 'secret'
        external.write_text('secret')
        link = directory / 'input/link'
        link.symlink_to(external)
        with self.assertRaises(TaskPathError):
            task_archive(task_id)
        link.unlink()
        os.mkfifo(directory / 'fifo')
        with self.assertRaises(TaskPathError):
            task_archive(task_id)
        (directory / 'fifo').unlink()


class MigrationTests(unittest.TestCase):
    def test_migration_preserves_unknown_source_and_allows_local_null(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'old.db'
            with sqlite3.connect(path) as db:
                db.execute("CREATE TABLE project_tasks(task_id TEXT PRIMARY KEY, projectID TEXT NOT NULL, ip_id TEXT NOT NULL DEFAULT '')")
                db.execute("INSERT INTO project_tasks VALUES ('old', 'p', 'id')")
            store = ProjectStore(path)
            try:
                self.assertEqual(store.all_entries()[0]['keti'], None)
                self.assertEqual(store.entries('p', 'keti2'), [])
                self.assertEqual(store.entries('p', 'keti3'), [])
                store.add('local', None, '', None)
                self.assertEqual(store.tasks('p'), ['old'])
                self.assertFalse(next(r for r in store.db.execute('PRAGMA table_info(project_tasks)') if r[1] == 'projectID')[3])
            finally:
                store.close()

    def test_local_api_and_zip_download(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / 'dataset'
            (data / 'ip/Demo').mkdir(parents=True)
            (data / 'include').mkdir()
            (data / 'ip/Demo/main.c').write_text('code')
            async def run(task):
                task.set_status('completed')
            with patch.object(config, 'VIP_TASK_DIR', root / 'tasks'), patch.object(config, 'VIP_DATASET_DIR', data), \
                 patch.dict(os.environ, {'VIP_PROJECT_DB': str(root / 'test.db')}), patch.object(Task, 'run', run), \
                 TestClient(create_app(True)) as client:
                self.assertEqual(client.get('/task/list_dataset').json()['ips'], [{'ip_name': 'Demo'}])
                response = client.post('/task/create_task', json={'ip_name': 'Demo', 'tool': 'KLEE', 'userprompt': ''})
                self.assertEqual(response.status_code, 201)
                task_id = response.json()['task_id']
                self.assertEqual(client.get('/task/list_tasks', params={'task_id': task_id}).json()['tasks'][0]['ip_name'], 'Demo')
                downloaded = client.get('/task/download_task', params={'task_id': task_id})
                self.assertEqual(downloaded.status_code, 200)
                self.assertIn('attachment', downloaded.headers['content-disposition'])
                self.assertEqual(client.get('/project/get_progress', params={'projectID': 'p'}).status_code, 422)
                self.assertEqual(client.post('/project/delete_project', json={'projectID': 'p'}).status_code, 422)
                self.assertEqual(client.post('/task/create_task', json={'ip_name': 'Demo', 'tool': 'invalid'}).status_code, 422)
