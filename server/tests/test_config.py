"""检查业务配置归属及调用方使用配置的行为。"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.config import VIP_ROOT
from app.agent import config as agent_config
from app.agent.pi import PiAgent
from app.service import config as service_config
from app.vip_task import config as task_config
from app.vip_task.task import Task, TaskReadLimitError
from app.vip_task.task_manager import TaskManager
from main import create_app


class ConfigTests(unittest.TestCase):
    def test_default_paths(self):
        self.assertEqual(VIP_ROOT, Path(__file__).resolve().parents[2])
        self.assertEqual(service_config.VIP_WEBUI_DIST_DIR, VIP_ROOT / 'webui/dist')
        self.assertEqual(task_config.VIP_TASK_DIR, VIP_ROOT / 'tasks')
        self.assertEqual(task_config.VIP_SKILL_DIR, VIP_ROOT / 'skills')
        self.assertEqual(task_config.VIP_DATASET_DIR, VIP_ROOT / 'dataset/16-ip')

    def test_agent_command(self):
        with patch('app.agent.pi.subprocess.Popen') as popen, \
                patch.object(agent_config, 'PI_EXECUTABLE', 'custom-pi'):
            agent = PiAgent('/tmp', session_dir='/tmp/session')
            self.assertEqual(popen.call_args.args[0],
                             ['custom-pi', '--mode', 'rpc', '--session-dir', '/tmp/session'])
            self.assertEqual(agent.close_timeout, agent_config.PI_CLOSE_TIMEOUT)
            PiAgent('/tmp', argv=['another-pi'], close_timeout=None)
            self.assertEqual(popen.call_args.args[0], ['another-pi'])

    def test_task_agent_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / 'tasks/case_1/workspace'
            workspace.mkdir(parents=True)
            skill = root / 'skills'
            skill.mkdir()
            with patch.object(task_config, 'VIP_TASK_DIR', root / 'tasks'), \
                    patch.object(task_config, 'VIP_SKILL_DIR', skill), \
                    patch.object(task_config, 'VIP_DATASET_DIR', root / 'input'), \
                    patch.object(task_config, 'PI_TOOLS', 'read,bash'), \
                    patch.object(agent_config, 'PI_EXECUTABLE', 'custom-pi'), \
                    patch('app.vip_task.task.PiAgent') as agent:
                Task('case_1')._create_agent()
                argv = agent.call_args.kwargs['argv']
                self.assertEqual(argv[0], 'custom-pi')
                self.assertEqual(argv[argv.index('--tools') + 1], 'read,bash')
                self.assertEqual(argv[argv.index('--skill') + 1], str(skill))
                self.assertIn(str(root / 'input'), argv[-1])
                self.assertEqual(agent.call_args.kwargs['cwd'], workspace)

    def test_workspace_limits_and_api(self):
        with tempfile.TemporaryDirectory() as tmp, \
                patch.object(task_config, 'VIP_TASK_DIR', Path(tmp)):
            directory = Path(tmp) / 'case_1'
            workspace = directory / 'workspace'
            workspace.mkdir(parents=True)
            (directory / 'task.json').write_text(json.dumps({
                'status': 'completed', 'created_at': '2026-01-01T00:00:00+00:00',
            }))
            (workspace / 'example.txt').write_text('test')
            self.assertEqual(TaskManager().list_tasks()['tasks'][0]['task_id'], 'case_1')
            with patch.object(task_config, 'MAX_SCAN_ENTRIES', 0):
                with self.assertRaises(TaskReadLimitError):
                    Task('case_1').get_task()
            with TestClient(create_app(backend_only=True)) as client:
                self.assertEqual(client.get('/task/list_tasks').status_code, 200)
                self.assertEqual(client.get('/task/get_task', params={'task_id': 'case_1'}).status_code, 200)
                with patch.object(task_config, 'MAX_WORKSPACE_FILES', 0):
                    self.assertEqual(client.get('/task/get_task', params={'task_id': 'case_1'}).status_code, 413)
                self.assertEqual(client.delete('/task/delete_task', params={'task_id': 'case_1'}).status_code, 200)
                self.assertFalse(directory.exists())


if __name__ == '__main__':
    unittest.main()
