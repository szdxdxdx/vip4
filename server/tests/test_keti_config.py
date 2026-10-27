"""课题配置持久化与运行时生效。"""
import json
import runpy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.service.config_api import router
from app.vip_task import config
from app.vip_task.keti2_sources import Keti2Sources
from app.vip_task.keti3_sources import Keti3Sources


class KetiConfigTest(unittest.TestCase):
    def test_save_reload_and_live_sources(self):
        app = FastAPI()
        app.include_router(router)
        with tempfile.TemporaryDirectory() as directory, patch.dict(config.__dict__, config.get_keti_config()):
            root = Path(directory)
            with patch.object(config, 'KETI_CONFIG_FILE', root / 'keti-ip.json'):
                two, three = Keti2Sources(), Keti3Sources()
                values = config.get_keti_config()
                values.update(KETI2_BASE_URL='http://keti2.test:8877', KETI3_BASE_URL='http://keti3.test:50053')
                with TestClient(app) as client:
                    self.assertEqual(client.put('/api/config/keti-ip', json=values).status_code, 200)
                    self.assertEqual(client.get('/api/config/keti-ip').json(), values)
                    self.assertEqual(client.put('/api/config/keti-ip', json={}).status_code, 422)
                self.assertTrue(two.config.search_url.startswith(values['KETI2_BASE_URL']))
                self.assertEqual(three.base_url, values['KETI3_BASE_URL'])
                self.assertEqual(json.loads(config.KETI_CONFIG_FILE.read_text()), values)
                self.assertEqual(config.KETI_CONFIG_FILE.stat().st_mode & 0o777, 0o600)
                with patch('app.config.VIP_ROOT', root):
                    restored = runpy.run_module('app.vip_task.config', run_name='app.vip_task._config_test')
                self.assertEqual(restored['get_keti_config'](), values)
                with patch.object(config, 'KETI_CONFIG_FILE', root / 'missing' / 'keti-ip.json'):
                    with self.assertRaises(OSError):
                        config.save_keti_config({**values, 'KETI2_BASE_URL': 'http://failed.test'})
                self.assertEqual(config.get_keti_config(), values)
