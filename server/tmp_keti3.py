"""课题三临时后端：模拟打包接口，只服务 `tmp/NWM_synthesis.zip`。

接口与 `/app/vip4/tmp/课题三接口.md` 一致：POST /api/verify 请求打包，GET /api/download/<文件> 下载压缩包。
仅接受唯一 projectID，直接运行本脚本即可：`python3 tmp_keti3.py`
"""
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

HOST = '127.0.0.1'
PORT = 50053
PROJECT_ID = '1001'
ARCHIVE = Path(__file__).resolve().parents[1] / 'tmp' / 'NWM_synthesis.zip'
LOG_FORMAT = '%(asctime)s tmp_keti3 %(levelname)s %(message)s'

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def do_POST(self):
        if urlsplit(self.path).path != '/api/verify':
            self._json(404, {'success': False, 'error': '未知接口'})
            return
        try:
            payload = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))) or b'{}')
        except (ValueError, TypeError):
            self._json(400, {'success': False, 'error': '请求正文必须是 JSON 对象'})
            return
        project_id = payload.get('project_id') if isinstance(payload, dict) else None
        if str(project_id) != PROJECT_ID:
            self._json(404, {'success': False, 'error': f'项目不存在，本临时后端仅支持 {PROJECT_ID}'})
            return
        if not ARCHIVE.is_file():
            self._json(500, {'success': False, 'error': f'缺少压缩包 {ARCHIVE}'})
            return
        self._json(200, {
            'success': True,
            'project': ARCHIVE.stem.removesuffix('_synthesis'),
            'result_dir': str(ARCHIVE.parent / 'res' / f'{PROJECT_ID}_dist' / 'DIST'),
            'zip_path': str(ARCHIVE),
            'zip_url': f'/api/download/{ARCHIVE.name}',
            'zip_size': ARCHIVE.stat().st_size,
        })

    def do_GET(self):
        self._download(True)

    def do_HEAD(self):
        self._download(False)

    def _download(self, body: bool):
        path = urlsplit(self.path).path
        prefix = '/api/download/'
        name = unquote(path[len(prefix):]) if path.startswith(prefix) else ''
        if name != ARCHIVE.name or not ARCHIVE.is_file():
            self._json(404, {'success': False, 'error': '压缩包不存在'}, body)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'application/zip')
        self.send_header('Content-Length', str(ARCHIVE.stat().st_size))
        self.end_headers()
        if not body:
            return
        with ARCHIVE.open('rb') as source:
            while chunk := source.read(1 << 16):
                self.wfile.write(chunk)

    def _json(self, status: int, payload: dict, body: bool = True):
        data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        if body:
            self.wfile.write(data)

    def log_message(self, message, *args):
        logger.info('%s %s', self.address_string(), message % args)


if __name__ == '__main__':
    logger.info('临时课题三后端 http://%s:%s，projectID=%s，压缩包=%s', HOST, PORT, PROJECT_ID, ARCHIVE)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
