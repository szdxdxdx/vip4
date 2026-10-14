"""本地输入及统一任务配置；用户段与默认业务说明分离。"""
import csv
import json
import secrets
import shutil
import sqlite3
import string
from datetime import datetime

from . import config
from .task import TaskExistsError, _write_metadata

class CreationRollbackError(Exception):
    def __init__(self, task_id):
        self.task_id = task_id
        super().__init__('任务写入失败且目录回滚失败')


TOOLS = ('CBMC', 'CPAchecker', 'KLEE')
DEFAULTS = {
    None: '本地数据集的形式模型和代码遵循 verify-ip SKILL；保留 ip 与 include 相对目录。',
    'keti2': '课题二形式模型格式和代码组织可能不同于本地数据集，请理解实际模型并适配验证流程。',
    'keti3': '课题三整个产物视为一个 IP；IR 是形式模型，产物根层 .c/.h 是主代码，iplib 等子目录是依赖；保留原编码，缺模型时明确报告。',
}


def instructions(directory, tool, keti, userprompt):
    # 自动 ID 确定后展开模板路径，避免用户段遗留任务占位符。
    userprompt = (userprompt or '').replace('<task_id>', directory.name)
    return (f'使用 verify-ip SKILL，使用 {tool} 验证软件 IP。\n'
            f'{DEFAULTS[keti]}\n只读输入：{directory / "input"}；来源清单：{directory / "files.csv"}。\n'
            f'报告、驱动、配置和工具输出按 SKILL 约定写入 {directory / "workspace"}/<tool>_suite/output，临时文件写入 workspace/tmp。\n'
            '如果 userpropmt 中有内容，则以 userpropmt 为准。\n'
            f'<userpropmt>\n{userprompt or ""}\n</userpropmt>')


def create_registered(manager, store, ip_name, tool, userprompt, *, project_id=None, keti=None, ip_id=''):
    for _ in range(1000):
        task_id = datetime.now().strftime('%m%d') + ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(4))
        if store.has_task(task_id) or task_id in manager.tasks or task_id in manager.deleting:
            continue
        directory = (config.VIP_TASK_DIR / task_id).resolve()
        try:
            result = manager.create_task(task_id, instructions(directory, tool, keti, userprompt), start=False)
        except TaskExistsError:
            continue
        try:
            path = directory / 'task.json'
            metadata = json.loads(path.read_text(encoding='utf-8'))
            metadata.update(ip_name=ip_name, tool=tool)
            _write_metadata(path, metadata)
            store.add(task_id, project_id, ip_id, keti)
        except Exception as error:
            try:
                manager.tasks[task_id].delete_files()
                manager.tasks.pop(task_id, None)
            except Exception:
                raise CreationRollbackError(task_id) from error
            if isinstance(error, sqlite3.IntegrityError) and store.has_task(task_id):
                continue
            raise
        return result
    raise RuntimeError('无法分配任务 ID：碰撞重试次数超限')


def dataset_list():
    root = config.VIP_DATASET_DIR / 'ip'
    return {'ips': [{'ip_name': path.name} for path in sorted(root.iterdir())
                    if path.is_dir() and not path.is_symlink()] if root.is_dir() else [], 'tools': list(TOOLS)}


def dataset_ip(ip_name):
    root = (config.VIP_DATASET_DIR / 'ip').resolve()
    path = root / ip_name
    if path.parent != root or path.is_symlink() or not path.is_dir():
        raise ValueError('数据集 IP 不存在或名称不合法')
    return path


def collect_local(ip_name, directory):
    # 整体复制 IP 与共享 include，保留原来的相对引用结构。
    roots = [dataset_ip(ip_name), config.VIP_DATASET_DIR / 'include']
    for root in roots:
        if root.is_symlink() or not root.is_dir():
            raise ValueError('数据集目录不存在或不安全')
        for path in root.rglob('*'):
            if path.is_symlink() or not (path.is_file() or path.is_dir()):
                raise ValueError('数据集不允许符号链接或特殊文件')
    with (directory / 'files.csv').open('w', encoding='utf-8', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=['ipId', 'source', 'field', 'path'])
        writer.writeheader()
        for root in roots:
            target = directory / 'input' / root.relative_to(config.VIP_DATASET_DIR)
            shutil.copytree(root, target)
            for path in sorted(root.rglob('*')):
                if path.is_file():
                    writer.writerow({'ipId': ip_name, 'source': str(path), 'field': 'dataset',
                                     'path': str(target / path.relative_to(root))})


async def create_local(manager, store, ip_name, tool, userprompt):
    dataset_ip(ip_name)
    result = create_registered(manager, store, ip_name, tool, userprompt)
    task_id = result['task_id']
    try:
        await manager.prepare_task(task_id, collect_local, ip_name, config.VIP_TASK_DIR / task_id)
    except BaseException:
        await manager.delete_task(task_id)
        raise
    manager._schedule(manager.tasks[task_id])
    return {**result, 'status': 'queued'}
