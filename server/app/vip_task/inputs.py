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

def instructions(directory, ip_name, tool, keti, userprompt):
    prompt = f"""
<task_prompt>
请你使用 SKILL verify-ip，对指定的软件 IP 进行形式化验证，严格遵循 SKILL 工作流的步骤执行验证任务

待验证的 IP：{ip_name}
使用的验证工具：{tool}
验证任务的工作目录是：`{directory / "workspace"}`

待验证的 IP 相关文件位于 `{directory / "input"}`
> 待验证的 IP 相关文件实际拷贝自其他目录或下载自网络，若需要查明，详见 `{directory / "files.csv"}`

要求：
- 不要读写未提及的其他目录中的文件；禁止修改工作目录意外的文件
- 争取在一轮对话内完成任务，不限制工具调用次数
- 执行全面、完整、严格的验证，给出有效的验证结论
- 只有生成最终验证结果报告，任务才算完成。完成任务后，只需在会话中答复【任务已完成】
</task_prompt>
"""
    if keti:
        prompt += f"""
补充说明：实际验证任务中提供的形式模型格式可能与 SKILL 约定的输入格式不同，请理解实际的形式模型，并适配验证流程，将形式模型转换成 SKILL 约定的 IR 格式
"""
    if userprompt:
        prompt += f"""

----------

以上为默认的验证任务说明，下方为用户根据实际业务情况，提供的额外说明。
- 需要同时理解默认业务说明和用户说明
- 若用户补充说明与默认说明有冲突，必须以用户的为准
- 若用户的说明与默认说明不冲突，请同时遵循两者的要求。
<userpropmt>
{userprompt.replace('<task_id>', directory.name)}
</userpropmt>
"""
    return prompt


def create_registered(manager, store, ip_name, tool, userprompt, *, project_id=None, keti=None, ip_id='', timestamp=None, keti5=None):
    from .timestamp import new_timestamp
    timestamp = timestamp or new_timestamp()
    for _ in range(1000):
        task_id = datetime.now().strftime('%m%d') + ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(4))
        if store.has_task(task_id) or task_id in manager.tasks or task_id in manager.deleting:
            continue
        directory = (config.VIP_TASK_DIR / task_id).resolve()
        try:
            result = manager.create_task(task_id, instructions(directory, ip_name, tool, keti, userprompt), start=False)
        except TaskExistsError:
            continue
        try:
            path = directory / 'task.json'
            metadata = json.loads(path.read_text(encoding='utf-8'))
            metadata.update(ip_name=ip_name, tool=tool, timestamp=timestamp, keti5=keti5)
            _write_metadata(path, metadata)
            store.add(task_id, project_id, ip_id, keti, timestamp)
        except Exception as error:
            try:
                manager.tasks[task_id].delete_files()
                manager.tasks.pop(task_id, None)
            except Exception:
                raise CreationRollbackError(task_id) from error
            if isinstance(error, sqlite3.IntegrityError) and store.has_task(task_id):
                continue
            raise
        return {**result, 'timestamp': timestamp}
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
