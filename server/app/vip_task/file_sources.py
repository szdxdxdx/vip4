"""项目接口及输入文件来源；本机文件及课题二文件下载。"""
import csv
import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)
FIELDS = (
    'ipMsg.entity.entityImplementation.dotC',
    'ipMsg.entity.entityImplementation.dotH',
    'ipMsg.formalModel.stateMachine',
    'ipMsg.formalModel.contracts',
    'ipMsg.formalModel.nonfunctionalConstraint',
    'ipMsg.formalModel.invariant',
)


@dataclass
class SourceConfig:
    search_url: str = 'http://8.130.30.48:8877/api/search/searchSoftwareIPByProjectId'
    path_map: dict[str, str] = field(default_factory=dict)
    download_url: str = 'http://8.130.30.48:8877/api/file/downloadFile'
    timeout: float = 30

    @classmethod
    def from_env(cls):
        mapping = json.loads(os.getenv('VIP_SOURCE_PATH_MAP', '{}'))
        if not isinstance(mapping, dict) or not all(
            isinstance(k, str) and k and isinstance(v, str) for k, v in mapping.items()
        ):
            raise ValueError('VIP_SOURCE_PATH_MAP 必须为非空路径前缀到本机目录的 JSON 对象')
        return cls(
            search_url=os.getenv('VIP_PROJECT_SEARCH_URL', cls.search_url),
            path_map=mapping,
            download_url=os.getenv('VIP_SOURCE_DOWNLOAD_URL', cls.download_url),
            timeout=float(os.getenv('VIP_SOURCE_TIMEOUT', '30')),
        )


class FileSources:
    def __init__(self, config: SourceConfig | None = None):
        self.config = config or SourceConfig.from_env()

    def search(self, project_id: str) -> list[dict]:
        separator = '&' if '?' in self.config.search_url else '?'
        url = self.config.search_url + separator + 'projectId=' + quote(project_id, safe='')
        logger.info('查询项目输入 projectID=%s', project_id)
        with urlopen(url, timeout=self.config.timeout) as response:
            payload = json.load(response)
        if not isinstance(payload, dict) or payload.get('code') != 0:
            raise ValueError('项目查询失败：响应 code 必须为 0')
        items = payload.get('result')
        if not isinstance(items, list):
            raise ValueError('项目查询失败：result 必须为列表')
        for item in items:
            if not isinstance(item, dict) or item.get('ipId') is None:
                raise ValueError('项目查询失败：每项必须包含 ipId')
        return items

    @staticmethod
    def fields(item: dict):
        for field_name in FIELDS:
            value = item
            for key in field_name.split('.'):
                value = value.get(key) if isinstance(value, dict) else None
            values = value if isinstance(value, list) else [value]
            for source in values:
                if source is None or source == '' or source == '无':
                    continue
                if not isinstance(source, str):
                    raise ValueError(f'{field_name} 必须为文件路径字符串或字符串列表')
                source = source.strip()
                if source and source != '无':
                    yield field_name, source

    def _copy(self, source: str, target: Path):
        if urlsplit(source).scheme in ('http', 'https'):
            request = source
        else:
            # 优先使用显式映射和本机文件，不可读时调用课题二下载接口。
            path = Path(source)
            for prefix, local in sorted(self.config.path_map.items(), key=lambda pair: -len(pair[0])):
                prefix = prefix.rstrip('/\\')
                if source == prefix or source.startswith(prefix + '/') or source.startswith(prefix + '\\'):
                    base = Path(local).expanduser().resolve()
                    path = base / source[len(prefix):].lstrip('/\\').replace('\\', '/')
                    if not path.resolve().is_relative_to(base):
                        raise ValueError(f'来源路径超出映射目录：{source}')
                    break
            if path.is_file() and os.access(path, os.R_OK):
                shutil.copyfile(path, target)
                return
            if not self.config.download_url:
                raise FileNotFoundError(f'来源不可读且未配置文件下载接口：{source}')
            if urlsplit(self.config.download_url).scheme not in ('http', 'https'):
                raise ValueError('文件下载接口必须使用 http(s) URL')
            request = Request(
                self.config.download_url,
                data=json.dumps({'filePath': source}, ensure_ascii=False).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
        logger.info('下载输入文件 source=%s', source)
        with urlopen(request, timeout=self.config.timeout) as response, target.open('wb') as output:
            shutil.copyfileobj(response, output)

    def collect(self, item: dict, task_dir: Path):
        directory = task_dir.resolve() / 'input'
        # 不重建任务根目录，避免删除任务时收集线程将其复活。
        directory.mkdir(exist_ok=True)
        count = 0
        used = set()
        with (task_dir / 'files.csv').open('w', encoding='utf-8', newline='') as output:
            writer = csv.DictWriter(output, fieldnames=['ipId', 'source', 'field', 'path'])
            writer.writeheader()
            for field_name, source in self.fields(item):
                name = Path(unquote(urlsplit(source).path).replace('\\', '/')).name
                if not name or name in ('.', '..'):
                    name = field_name.rsplit('.', 1)[-1]
                # 所有输入在同一目录；重复 basename 加后缀，绝不覆盖。
                candidate = name
                index = 2
                while candidate in used:
                    p = Path(name)
                    candidate = f'{p.stem}_{index}{p.suffix}'
                    index += 1
                used.add(candidate)
                target = directory / candidate
                self._copy(source, target)
                writer.writerow({'ipId': str(item['ipId']), 'source': source,
                                 'field': field_name, 'path': str(target)})
                output.flush()
                count += 1
        if not count:
            raise ValueError(f'IP {item["ipId"]} 没有可收集的输入文件')
        logger.info('输入收集完成 task_id=%s files=%s', task_dir.name, count)
