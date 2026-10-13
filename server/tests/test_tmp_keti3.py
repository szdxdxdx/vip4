"""临时课题三后端与课题三适配器的联调测试；本项目内闭环，不访问外部网络。"""
import json
import tempfile
import threading
import unittest
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import tmp_keti3
from app.vip_task.keti3_sources import Keti3Sources


class TmpKeti3Tests(unittest.TestCase):
    def setUp(self):
        self.archive = Path(tempfile.mkdtemp()) / 'sample.zip'
        with zipfile.ZipFile(self.archive, 'w') as archive:
            archive.writestr('NWM.c', b'int main(void) { return 0; }')
            archive.writestr('IR/NWM.esaml', b'model')
        self.original = tmp_keti3.ARCHIVE
        tmp_keti3.ARCHIVE = self.archive
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), tmp_keti3.Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f'http://127.0.0.1:{self.server.server_address[1]}'

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        tmp_keti3.ARCHIVE = self.original

    def verify(self, project_id):
        request = Request(self.base + '/api/verify', data=json.dumps({'project_id': project_id}).encode(),
                          headers={'Content-Type': 'application/json'}, method='POST')
        return urlopen(request, timeout=10)

    def test_interface_matches_specification_and_serves_the_archive(self):
        with self.verify('1001') as response:
            self.assertEqual(response.headers['Content-Type'], 'application/json; charset=utf-8')
            payload = json.load(response)
        self.assertEqual(payload['success'], True)
        self.assertEqual(payload['project'], 'sample')
        self.assertEqual(payload['zip_url'], '/api/download/sample.zip')
        self.assertEqual(payload['zip_size'], self.archive.stat().st_size)
        with urlopen(self.base + payload['zip_url'], timeout=10) as response:
            self.assertEqual(response.headers['Content-Type'], 'application/zip')
            self.assertEqual(response.read(), self.archive.read_bytes())

    def expect_404(self, request):
        with self.assertRaises(HTTPError) as error:
            urlopen(request, timeout=10)
        self.assertEqual(error.exception.code, 404)
        error.exception.close()

    def test_unknown_project_and_unknown_file_are_rejected(self):
        for project_id in ['1002', '', None]:
            request = Request(self.base + '/api/verify',
                              data=json.dumps({'project_id': project_id}).encode(),
                              headers={'Content-Type': 'application/json'}, method='POST')
            self.expect_404(request)
        self.expect_404(self.base + '/api/download/other.zip')

    def test_adapter_collects_the_temporary_backend_archive(self):
        sources = Keti3Sources(self.base, timeout=10)
        items = sources.search('1001')
        self.assertEqual([item['ipId'] for item in items], ['keti3:1001'])
        with tempfile.TemporaryDirectory() as directory:
            task = Path(directory)
            sources.collect(items[0], task)
            self.assertEqual((task / 'input' / 'NWM.c').read_bytes(), b'int main(void) { return 0; }')
            self.assertEqual((task / 'input' / 'IR' / 'NWM.esaml').read_bytes(), b'model')
            self.assertEqual((task / 'keti3.zip').read_bytes(), self.archive.read_bytes())


if __name__ == '__main__':
    unittest.main()
