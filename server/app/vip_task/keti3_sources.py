"""课题三产物打包、下载与解压；整个产物作为一个特殊软件 IP。"""
import csv
import json
import logging
import os
import re
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote, unquote, urljoin, urlsplit
from urllib.request import Request, urlopen

from . import config

logger = logging.getLogger(__name__)
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_INPUT_BYTES = 1024 * 1024 * 1024
MAX_ENTRIES = 10000



class Keti3Sources:
    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self._base_url = base_url
        self.timeout = timeout if timeout is not None else float(os.getenv('VIP_KETI3_TIMEOUT', '120'))

    @property
    def base_url(self):
        return (self._base_url if self._base_url is not None else config.KETI3_BASE_URL).rstrip('/')

    def _base(self):
        parts = urlsplit(self.base_url)
        if parts.scheme not in ('http', 'https') or not parts.netloc or parts.path or parts.query or parts.fragment:
            raise ValueError('请配置 vip_task/config.py 的 KETI3_BASE_URL 为课题三服务地址，例如 http://主机:50053（不含 /api）')
        return parts

    def _download_url(self, value):
        base = self._base()
        if not isinstance(value, str) or not value.strip():
            raise ValueError('课题三打包响应缺少 zip_url')
        parts = urlsplit(urljoin(self.base_url + '/', value))
        if (parts.scheme, parts.netloc) != (base.scheme, base.netloc) or not parts.path.startswith('/api/download/') or parts.query or parts.fragment:
            raise ValueError('课题三 zip_url 必须是本服务的 /api/download/ 下载地址')
        name = unquote(parts.path.removeprefix('/api/download/'))
        if not name or name in ('.', '..') or '/' in name or chr(92) in name:
            raise ValueError('课题三 zip_url 必须指向单个压缩包文件')
        return parts._replace(path=quote(parts.path, safe='/%:')).geturl()

    def validate(self, project_id: str):
        # 提交前检查本地配置与参数，避免强制覆盖先删数据再发现配置错误。
        self._base()
        if not re.fullmatch(r'[1-9][0-9]*', project_id):
            raise ValueError('课题三 projectID 必须是正整数的字符串')

    def search(self, project_id: str) -> list[dict]:
        self.validate(project_id)
        request = Request(self.base_url + '/api/verify',
                          data=json.dumps({'project_id': project_id}).encode('utf-8'),
                          headers={'Content-Type': 'application/json'}, method='POST')
        logger.info('课题三打包产物 projectID=%s', project_id)
        with urlopen(request, timeout=self.timeout) as response:
            payload = json.load(response)
        if not isinstance(payload, dict) or payload.get('success') is not True:
            message = payload.get('message', 'success 不为 true') if isinstance(payload, dict) else '响应不是 JSON 对象'
            raise ValueError(f'课题三打包失败：{message}')
        download_url = self._download_url(payload.get('zip_url'))
        return [{'ipId': f'keti3:{project_id}',
                 'ipMsg': {'entity': {'basicInformation': {'id': f'keti3:{project_id}', 'name': payload.get('project') if isinstance(payload.get('project'), str) else f'keti3:{project_id}'}}},
                 'zip_url': download_url}]

    @staticmethod
    def _entries(archive: zipfile.ZipFile, directory: Path):
        entries = archive.infolist()
        if len(entries) > MAX_ENTRIES or sum(entry.file_size for entry in entries) > MAX_INPUT_BYTES:
            raise ValueError('课题三压缩包条目数或解压大小超出限制')
        targets = {}
        for entry in entries:
            name = entry.filename.replace(chr(92), '/')
            path = PurePosixPath(name)
            mode = stat.S_IFMT(entry.external_attr >> 16)
            if (not name or chr(0) in name or path.is_absolute() or '..' in path.parts
                    or not path.parts or ':' in path.parts[0]
                    or mode not in (0, stat.S_IFREG, stat.S_IFDIR)):
                raise ValueError(f'课题三压缩包含不安全路径或特殊文件：{entry.filename}')
            target = directory.joinpath(*path.parts)
            if not target.resolve().is_relative_to(directory) or target.exists() or target.is_symlink() or target in targets:
                raise ValueError(f'课题三压缩包路径冲突：{entry.filename}')
            targets[target] = entry
        for target in targets:
            if any(parent in targets and not targets[parent].is_dir() for parent in target.parents):
                raise ValueError('课题三压缩包存在文件与目录冲突')
        if not any(not entry.is_dir() for entry in entries):
            raise ValueError('课题三压缩包没有输入文件')
        return targets.items()

    def collect(self, item: dict, task_dir: Path):
        # 收集线程由 TaskManager 管理；删除任务前必须等待此线程结束。
        task_dir = task_dir.resolve(strict=True)
        directory = task_dir / 'input'
        if directory.is_symlink():
            raise ValueError('课题三输入目录不能是符号链接')
        directory.mkdir(exist_ok=True)
        url = self._download_url(item['zip_url'])
        archive_path = task_dir / 'keti3.zip'
        size = 0
        logger.info('下载课题三产物 task_id=%s source=%s', task_dir.name, url)
        with urlopen(url, timeout=self.timeout) as response, archive_path.open('xb') as output:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_ARCHIVE_BYTES:
                    raise ValueError('课题三压缩包下载大小超出限制')
                output.write(chunk)
        count = 0
        with zipfile.ZipFile(archive_path) as archive, (task_dir / 'files.csv').open('w', encoding='utf-8', newline='') as output:
            writer = csv.DictWriter(output, fieldnames=['ipId', 'source', 'field', 'path'])
            writer.writeheader()
            writer.writerow({'ipId': item['ipId'], 'source': url, 'field': 'keti3.archive', 'path': str(archive_path)})
            output.flush()
            for target, entry in self._entries(archive, directory):
                if entry.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(entry) as source, target.open('xb') as saved:
                    shutil.copyfileobj(source, saved, length=1024 * 1024)
                writer.writerow({'ipId': item['ipId'], 'source': url + '#' + quote(entry.filename, safe='/'),
                                 'field': 'keti3.archive.member', 'path': str(target)})
                output.flush()
                count += 1
        logger.info('课题三输入准备完成 task_id=%s files=%s bytes=%s', task_dir.name, count, size)
