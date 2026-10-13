"""课题三使用 HTTP/ZIP 替身测试，不访问真实业务服务或 Pi。"""
import csv
import io
import json
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from app.vip_task.keti3_sources import Keti3Sources, VERIFICATION_PROMPT


def bundle(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, value in files:
            archive.writestr(name, value)
    return output.getvalue()


class Keti3Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.task = Path(self.temp.name) / 'single'
        self.task.mkdir()
        (self.task / 'input').mkdir()
        self.sources = Keti3Sources('http://keti3.test:50053', timeout=15)
        self.item = {'ipId': 'keti3:1001', 'zip_url': 'http://keti3.test:50053/api/download/SAM.zip'}

    def collect(self, data):
        with patch('app.vip_task.keti3_sources.urlopen', return_value=io.BytesIO(data)) as get:
            self.sources.collect(self.item, self.task)
        self.assertEqual(get.call_args.args[0], self.item['zip_url'])

    def test_pack_request_constructs_exactly_one_ip_without_synthesis(self):
        response = {'success': True, 'zip_url': '/api/download/SAM.zip', 'project': 'SAM'}
        with patch('app.vip_task.keti3_sources.urlopen', return_value=io.BytesIO(json.dumps(response).encode())) as get:
            items = self.sources.search('1001')
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['ipMsg']['entity']['basicInformation']['id'], 'keti3:1001')
        self.assertEqual(items[0]['_verification_prompt'], VERIFICATION_PROMPT)
        request = get.call_args.args[0]
        self.assertEqual(request.full_url, 'http://keti3.test:50053/api/verify')
        self.assertEqual(request.get_method(), 'POST')
        self.assertEqual(json.loads(request.data), {'project_id': '1001'})
        self.assertEqual(get.call_args.kwargs['timeout'], 15)

    def test_all_files_keep_layout_and_original_encoding(self):
        raw = '// 中文代码'.encode('gbk')
        files = [('SAM.c', raw), ('SAM.h', b'header'), ('IR/model.json', b'{}'),
                 ('iplib/SAM.c', b'dependency'), ('req/example.spacerdl', b'model'), ('data.bin', bytes(range(256)))]
        data = bundle(files)
        self.collect(data)
        self.assertEqual((self.task / 'keti3.zip').read_bytes(), data)
        for name, content in files:
            self.assertEqual((self.task / 'input' / name).read_bytes(), content)
        with (self.task / 'files.csv').open(encoding='utf-8', newline='') as source:
            records = list(csv.DictReader(source))
        self.assertEqual(len(records), len(files) + 1)
        self.assertTrue(all(Path(row['path']).is_absolute() for row in records))
        self.assertEqual(records[0]['field'], 'keti3.archive')
        self.assertEqual(records[1]['source'], self.item['zip_url'] + '#SAM.c')
        self.assertIn('IR', VERIFICATION_PROMPT)
        self.assertIn('最外层', VERIFICATION_PROMPT)
        self.assertIn('GBK/gb18030', VERIFICATION_PROMPT)
        self.assertIn('规约缺失', VERIFICATION_PROMPT)

    def test_wrapping_directory_is_preserved(self):
        self.collect(bundle([('DIST/SAM.c', b'code'), ('DIST/IR/model', b'formal')]))
        self.assertTrue((self.task / 'input' / 'DIST' / 'IR' / 'model').is_file())

    def test_configuration_and_project_id_errors_do_not_send_http(self):
        with patch('app.vip_task.keti3_sources.urlopen') as get:
            for base in ['', 'file:///tmp', 'http://host/api', 'http://host?query=1']:
                with self.assertRaises(ValueError):
                    Keti3Sources(base).search('1001')
            for project_id in ['0', '-1', ' 1', 'abc', '1/2']:
                with self.assertRaises(ValueError):
                    self.sources.search(project_id)
        get.assert_not_called()

    def test_failed_or_missing_download_responses_are_rejected(self):
        for response in [[], {'success': False, 'message': '未找到产物'}, {'success': 1}, {'success': True}]:
            with self.subTest(response=response), patch('app.vip_task.keti3_sources.urlopen', return_value=io.BytesIO(json.dumps(response).encode())):
                with self.assertRaises(ValueError):
                    self.sources.search('1001')

    def test_download_url_is_bound_to_service(self):
        for url in ['http://other.test/api/download/a.zip', '/api/synthesize', '/api/download/../x',
                    '/api/download/%2e%2e%2fx', '/api/download/a%5cb.zip', '/api/download/a.zip?q=1']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.sources._download_url(url)
        self.assertEqual(self.sources._download_url('/api/download/代码.zip'),
                         'http://keti3.test:50053/api/download/%E4%BB%A3%E7%A0%81.zip')

    def test_zip_path_traversal_is_rejected_before_any_extraction(self):
        for name in ['../escape.c', '/tmp/escape.c', 'C:/escape.c', '..' + chr(92) + 'escape.c']:
            with self.subTest(name=name), patch('app.vip_task.keti3_sources.urlopen', return_value=io.BytesIO(bundle([('valid.c', b'code'), (name, b'escape')]))):
                with self.assertRaises(ValueError):
                    self.sources.collect(self.item, self.task)
            self.assertFalse((self.task / 'input' / 'valid.c').exists())
            (self.task / 'keti3.zip').unlink()
        self.assertFalse((self.task.parent / 'escape.c').exists())

    def test_zip_symlinks_and_colliding_paths_are_rejected(self):
        entry = zipfile.ZipInfo('link')
        entry.create_system = 3
        entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        archives = [bundle([(entry, '../outside')]), bundle([('a.c', b'a'), ('./a.c', b'b')]),
                    bundle([('folder', b'file'), ('folder/code.c', b'code')])]
        for data in archives:
            with patch('app.vip_task.keti3_sources.urlopen', return_value=io.BytesIO(data)), self.assertRaises(ValueError):
                self.sources.collect(self.item, self.task)
            (self.task / 'keti3.zip').unlink()
        self.assertEqual(list((self.task / 'input').iterdir()), [])

    def test_empty_corrupt_and_oversized_zip_do_not_produce_inputs(self):
        for data, error in [(bundle([]), ValueError), (b'not a zip', zipfile.BadZipFile)]:
            with patch('app.vip_task.keti3_sources.urlopen', return_value=io.BytesIO(data)), self.assertRaises(error):
                self.sources.collect(self.item, self.task)
            (self.task / 'keti3.zip').unlink()
        with patch('app.vip_task.keti3_sources.MAX_ARCHIVE_BYTES', 2), patch('app.vip_task.keti3_sources.urlopen', return_value=io.BytesIO(b'too big')), self.assertRaises(ValueError):
            self.sources.collect(self.item, self.task)
        (self.task / 'keti3.zip').unlink()
        with patch('app.vip_task.keti3_sources.MAX_INPUT_BYTES', 2), patch('app.vip_task.keti3_sources.urlopen', return_value=io.BytesIO(bundle([('code.c', b'large')]))), self.assertRaises(ValueError):
            self.sources.collect(self.item, self.task)
        self.assertEqual(list((self.task / 'input').iterdir()), [])

    def test_preexisting_input_is_never_overwritten(self):
        original = self.task / 'input' / 'SAM.c'
        original.write_bytes(b'keep original')
        with patch('app.vip_task.keti3_sources.urlopen', return_value=io.BytesIO(bundle([('SAM.c', b'new')]))), self.assertRaises(ValueError):
            self.sources.collect(self.item, self.task)
        self.assertEqual(original.read_bytes(), b'keep original')


class Keti3ProjectTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from app.vip_task.project import ProjectManager, ProjectStore
        from app.vip_task.task_manager import TaskManager
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = patch('app.vip_task.config.VIP_TASK_DIR', self.root / 'tasks')
        self.config.start()
        self.tasks = TaskManager()
        self.keti2 = unittest.mock.Mock()
        self.manager = ProjectManager(self.tasks, ProjectStore(self.root / 'projects.sqlite3'),
                                      sources=self.keti2, keti3_sources=Keti3Sources('http://keti3.test:50053'))
        self.data = bundle([('main.c', b'int main(void) {return 0;}'), ('main.h', b'header'),
                            ('IR/model.json', b'{}'), ('iplib/dependency.c', b'dependency')])

    async def asyncTearDown(self):
        await self.manager.close()
        await self.tasks.close()
        self.config.stop()
        self.temp.cleanup()

    def response(self, request, **kwargs):
        if isinstance(request, str):
            return io.BytesIO(self.data)
        return io.BytesIO(json.dumps({'success': True, 'zip_url': '/api/download/SAM.zip'}).encode())

    async def test_keti3_prepares_one_task_before_running_and_force_replaces_it(self):
        from app.vip_task.task import Task, _write_metadata
        seen = []
        async def run(task):
            self.assertTrue((task.task_dir / 'input' / 'IR' / 'model.json').is_file())
            self.assertTrue((task.task_dir / 'input' / 'main.c').is_file())
            self.assertTrue((task.task_dir / 'keti3.zip').is_file())
            self.assertTrue((task.task_dir / 'files.csv').is_file())
            self.assertIn(VERIFICATION_PROMPT, task.prompt)
            self.assertIn('检查入口函数', task.prompt)
            seen.append(task.task_id)
            metadata = Task._metadata(task.task_dir)
            metadata.update(status='completed', chatstatus='completed', verification_status='completed')
            _write_metadata(task.task_dir / 'task.json', metadata)
        with patch('app.vip_task.keti3_sources.urlopen', side_effect=self.response), patch.object(Task, 'run', run):
            await self.manager.submit('1001', '检查入口函数', source='keti3')
            await self.manager.jobs['1001']
            first = self.manager.progress('1001')
            self.assertEqual(first['source'], 'keti3')
            self.assertEqual(first['status'], 'completed')
            self.assertEqual(first['total'], 1)
            self.assertEqual(first['tasks'][0]['ip_id'], 'keti3:1001')
            old = first['tasks'][0]['task_id']
            self.assertRegex(old, r'^[0-9]{4}[a-z0-9]{4}$')
            await self.manager.submit('1001', '检查入口函数', source='keti3', force=True)
            await self.manager.jobs['1001']
            self.assertEqual(self.manager.progress('1001')['total'], 1)
            self.assertFalse((self.root / 'tasks' / old).exists())
            self.assertFalse(self.manager.store.has_task(old))
        self.assertEqual(len(seen), 2)
        self.keti2.search.assert_not_called()
        self.keti2.collect.assert_not_called()
        await self.manager.delete('1001')
        self.assertEqual(self.manager.store.tasks('1001'), [])
        from app.vip_task.project import ProjectNotFoundError
        with self.assertRaises(ProjectNotFoundError):
            self.manager.progress('1001')
        self.assertFalse((self.root / 'tasks' / seen[-1]).exists())

    async def test_bad_bundle_is_failed_without_starting_pi(self):
        from app.vip_task.task import Task
        self.data = bundle([('../escape.c', b'bad')])
        with patch('app.vip_task.keti3_sources.urlopen', side_effect=self.response), patch.object(Task, 'run') as run:
            await self.manager.submit('1001', source='keti3')
            await self.manager.jobs['1001']
        result = self.manager.progress('1001')
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['tasks'][0]['status'], 'failed')
        run.assert_not_called()
        self.assertFalse((self.root / 'tasks' / 'escape.c').exists())
        await self.manager.delete('1001')
        self.assertEqual(list((self.root / 'tasks').iterdir()), [])


if __name__ == '__main__':
    unittest.main()
