"""Run: .venv/bin/python -m unittest discover -s tests -v (no LLM jobs)."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import config
from app.app import create_app
from app.task.service import TaskManager, _write_metadata


class TaskReadAPITests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'tasks'
        self.patcher = patch.object(config, 'VIP_TASK_DIR', self.root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.client = self.enterContext(TestClient(create_app()))

    def task(self, name='older', created='2026-01-01T00:00:00+00:00'):
        directory = self.root / name
        workspace = directory / 'workspace'
        workspace.mkdir(parents=True)
        (directory / 'session').mkdir()
        (directory / 'session' / 'secret.txt').write_text('SESSION SECRET')
        (directory / 'task.json').write_text(json.dumps({
            'task_id': name, 'prompt': 'verify 中文', 'status': 'completed',
            'created_at': created, 'private': 'must not be returned',
            'reports': ['suite/output/report.json', '../session/secret.txt'],
        }))
        output = workspace / 'suite' / 'output'
        output.mkdir(parents=True)
        (output / 'report.html').write_text('<html><script>1</script>报告</html>')
        (output / 'report.json').write_text('{"ok":true}')
        (workspace / 'notes.txt').write_text('中文 notes')
        (workspace / 'evil.html').write_text('<script>alert(1)</script>')
        (workspace / 'evil.js').write_text('alert(1)')
        for hidden in ('tmp', '__pycache__', '.git', '.hidden'):
            (workspace / hidden).mkdir()
            (workspace / hidden / 'secret').write_text('excluded')
        (directory / 'events.jsonl').write_text('{"type":"agent","data":{"type":"done"}}\n')
        return workspace

    def get_file(self, path, task_id='older', **params):
        return self.client.get('/task/get_file', params={
            'task_id': task_id, 'path': path, **params,
        })

    def test_missing_root_and_tasks(self):
        self.assertEqual(self.client.get('/task/list_tasks').json(), {'tasks': []})
        self.assertEqual(self.client.get('/task/get_task', params={'task_id': 'missing'}).status_code, 404)
        self.assertEqual(self.get_file('report.html').status_code, 404)

    def test_list_details_and_safe_preview(self):
        workspace = self.task()
        self.task('newer', '2026-02-01T00:00:00+00:00')
        tasks = self.client.get('/task/list_tasks').json()['tasks']
        self.assertEqual([task['task_id'] for task in tasks], ['newer', 'older'])
        self.assertEqual(set(tasks[0]), {'task_id', 'prompt', 'status', 'created_at', 'reports'})
        self.assertEqual(tasks[0]['reports'], ['suite/output/report.json'])
        response = self.client.get('/task/get_task', params={'task_id': 'older'})
        self.assertEqual(response.status_code, 200)
        files = response.json()['files']
        self.assertEqual([file['path'] for file in files], [
            'suite/output/report.html', 'suite/output/report.json',
            'evil.html', 'evil.js', 'notes.txt',
        ])
        self.assertEqual(files[0]['kind'], 'report_html')
        self.assertEqual(files[1]['kind'], 'report_json')
        for file in files:
            self.assertEqual(file['size'], (workspace / file['path']).stat().st_size)
        self.assertEqual(response.json(), self.client.get('/task/get_task', params={'task_id': 'older'}).json())
        html = self.get_file('suite/output/report.html')
        self.assertEqual(html.status_code, 200)
        self.assertEqual(html.content, (workspace / 'suite/output/report.html').read_bytes())
        self.assertTrue(html.headers['content-type'].startswith('text/html'))
        self.assertTrue(html.headers['content-disposition'].startswith('inline;'))
        self.assertEqual(html.headers['content-security-policy'], 'sandbox allow-scripts')
        self.assertEqual(html.headers['x-content-type-options'], 'nosniff')
        download = self.get_file('suite/output/report.html', download='true')
        self.assertTrue(download.headers['content-disposition'].startswith('attachment;'))
        self.assertEqual(download.content, html.content)
        self.assertTrue(self.get_file('suite/output/report.json').headers['content-type'].startswith('application/json'))
        for filename in ('evil.html', 'evil.js', 'notes.txt'):
            self.assertTrue(self.get_file(filename).headers['content-type'].startswith('text/plain'))
        self.assertEqual(self.get_file('missing').status_code, 404)
        self.assertEqual(self.get_file('suite').status_code, 404)
        self.assertEqual(self.get_file('notes.txt/not-a-directory').status_code, 404)
        (workspace / 'manual.pdf').write_bytes(b'%PDF-1.4')
        pdf = self.get_file('manual.pdf')
        self.assertEqual(pdf.headers['content-type'], 'application/pdf')
        self.assertTrue(pdf.headers['content-disposition'].startswith('attachment;'))
        self.assertEqual(self.client.get('/task/get_events', params={'task_id': 'older'}).text,
                         '{"type":"agent","data":{"type":"done"}}\n')

    def test_list_sorts_actual_timestamps(self):
        self.task('early', '2026-01-01T01:00:00+02:00')
        self.task('late', '2026-01-01T00:00:00+00:00')
        self.assertEqual([t['task_id'] for t in self.client.get('/task/list_tasks').json()['tasks']],
                         ['late', 'early'])

    def test_invalid_paths_and_task_ids(self):
        self.task()
        for value in ('../task.json', '/etc/passwd', 'suite/../../session/secret.txt',
                      'suite//output/report.html', './notes.txt', 'C:/secret',
                      'suite\\output\\report.html', 'notes.txt\x00'):
            with self.subTest(path=value):
                self.assertEqual(self.get_file(value).status_code, 400)
        for value in ('tmp/secret', '__pycache__/secret', '.git/secret', '.hidden/secret'):
            self.assertEqual(self.get_file(value).status_code, 403)
        for value in ('../older', '/older', 'x' * 65, '', '.older'):
            self.assertEqual(self.client.get('/task/get_task', params={'task_id': value}).status_code, 422)
            self.assertEqual(self.get_file('notes.txt', task_id=value).status_code, 422)
        self.assertEqual(self.client.post('/task/create_task', json={'task_id': '../bad', 'prompt': 'x'}).status_code, 422)

    def test_symlink_boundaries_and_metadata(self):
        workspace = self.task()
        other = self.task('other')
        outside = Path(self.temporary.name) / 'secret'
        outside.write_text('OUTSIDE SECRET')
        (workspace / 'cross-task').symlink_to(other / 'notes.txt')
        (workspace / 'outside').symlink_to(outside)
        (workspace / 'session').symlink_to(workspace.parent / 'session', target_is_directory=True)
        (workspace / 'cross-dir').symlink_to(other, target_is_directory=True)
        for name in ('cross-task', 'outside', 'session/secret.txt', 'cross-dir/notes.txt'):
            self.assertEqual(self.get_file(name).status_code, 403)
        files = self.client.get('/task/get_task', params={'task_id': 'older'}).json()['files']
        self.assertFalse(any(file['path'].startswith(('cross-', 'outside', 'session')) for file in files))
        (self.root / 'alias').symlink_to(other.parent, target_is_directory=True)
        self.assertEqual(self.get_file('notes.txt', task_id='alias').status_code, 403)
        self.assertNotIn('alias', [t['task_id'] for t in self.client.get('/task/list_tasks').json()['tasks']])
        (workspace.parent / 'task.json').unlink()
        (workspace.parent / 'task.json').symlink_to(other.parent / 'task.json')
        self.assertEqual(self.client.get('/task/get_task', params={'task_id': 'older'}).status_code, 403)
        (workspace.parent / 'task.json').unlink()
        (workspace.parent / 'task.json').write_text('{bad')
        self.assertEqual(self.client.get('/task/get_task', params={'task_id': 'older'}).status_code, 500)
        self.assertEqual([t['task_id'] for t in self.client.get('/task/list_tasks').json()['tasks']], ['other'])

    def test_workspace_symlink_rejected(self):
        workspace = self.task()
        other = self.task('other')
        workspace.rename(workspace.parent / 'original')
        workspace.symlink_to(other, target_is_directory=True)
        self.assertEqual(self.get_file('notes.txt').status_code, 403)
        self.assertEqual(self.client.get('/task/get_task', params={'task_id': 'older'}).status_code, 403)
        workspace.unlink()
        workspace.symlink_to(workspace.parent / 'session', target_is_directory=True)
        self.assertEqual(self.get_file('secret.txt').status_code, 403)

    def test_scan_limit_and_disappearing_file(self):
        workspace = self.task()
        with patch('app.task.service.MAX_SCAN_ENTRIES', 1):
            self.assertEqual(self.client.get('/task/get_task', params={'task_id': 'older'}).status_code, 413)
        original = TaskManager._workspace_file
        def disappearing(root, value):
            if value == 'notes.txt':
                (workspace / value).unlink(missing_ok=True)
            return original(root, value)
        with patch.object(TaskManager, '_workspace_file', side_effect=disappearing):
            response = self.client.get('/task/get_task', params={'task_id': 'older'})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('notes.txt', [file['path'] for file in response.json()['files']])

    def test_atomic_metadata(self):
        workspace = self.task()
        path = workspace.parent / 'task.json'
        original = json.loads(path.read_text())
        errors = []
        done = threading.Event()
        def writer():
            try:
                for i in range(100):
                    _write_metadata(path, {**original, 'status': str(i)})
            except Exception as error:
                errors.append(error)
            finally:
                done.set()
        thread = threading.Thread(target=writer)
        thread.start()
        while not done.is_set():
            metadata = json.loads(path.read_text())
            self.assertEqual(metadata['private'], original['private'])
        thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(json.loads(path.read_text())['status'], '99')
        self.assertEqual(list(path.parent.glob('.task-*.tmp')), [])


if __name__ == '__main__':
    unittest.main()
