"""课题五参数快照、结果上传及批次结束通知。"""
import asyncio
import logging
import json
import os

import httpx

from .archive import task_archive
from .task import Task, TaskNotFoundError, _write_metadata

logger = logging.getLogger(__name__)
FIELDS = ('projectId', 'jobName', 'buildId', 'toolName', 'executionId')
TERMINAL = {'completed', 'failed', 'cancelled'}


def parameters(value):
    # 参数不全时整体忽略；所有标识始终以字符串落盘。
    if not isinstance(value, dict) or not all(isinstance(value.get(k), str) and value[k].strip() for k in FIELDS):
        return None
    return {key: value[key] for key in FIELDS}


def _upload(task_id, params):
    url = os.getenv('KETI5_UPLOAD_URL', '')
    if not url:
        raise ValueError('尚未配置 KETI5_UPLOAD_URL')
    archive = task_archive(task_id)
    try:
        with archive.open('rb') as source, httpx.Client(timeout=float(os.getenv('KETI5_TIMEOUT', '30'))) as client:
            response = client.post(url, data={
                'pipelineName': params['jobName'], 'buildId': params['buildId'], 'toolName': params['toolName'],
            }, files={'file': (f'{task_id}.zip', source, 'application/zip')})
            response.raise_for_status()
            if response.json().get('code') != 200:
                raise ValueError('工厂返回上传失败')
    finally:
        archive.unlink(missing_ok=True)


async def upload(task_id):
    directory = Task._task_dir(task_id)
    params = parameters(Task._metadata(directory).get('keti5'))
    if params is None:
        raise ValueError('此任务没有 keti5 参数，无法上传')
    failed = True
    job = asyncio.create_task(asyncio.to_thread(_upload, task_id, params))
    try:
        try:
            await asyncio.shield(job)
        except asyncio.CancelledError:
            # 取消也等上传线程退出，确保 ZIP 清理与元数据落盘。
            try:
                await job
                failed = False
            except Exception:
                logger.exception('keti5 取消期间上传失败 task_id=%s', task_id)
            raise
        failed = False
    finally:
        # 元数据只在事件循环中局部更新，不能在线程中覆盖验证终态。
        Task._metadata(directory)
        metadata = json.loads((directory / 'task.json').read_text(encoding='utf-8'))
        metadata['keti5_upload_failed'] = failed
        _write_metadata(directory / 'task.json', metadata)


def notify(params, progress):
    url = os.getenv('KETI5_CALLBACK_URL', '')
    if not url:
        raise ValueError('尚未配置 KETI5_CALLBACK_URL')
    payload = {key: params[key] for key in ('executionId', 'jobName', 'toolName')}
    # Python 整数及 JSON 编码不会经过浮点数，保留大整数精度。
    payload.update(buildId=int(params['buildId']), progress=progress, status=int(progress == 100))
    auth = (os.getenv('KETI5_JENKINS_USER', ''), os.getenv('KETI5_JENKINS_API_TOKEN', ''))
    with httpx.Client(timeout=float(os.getenv('KETI5_TIMEOUT', '30'))) as client:
        response = client.post(url, json=payload, auth=auth)
        response.raise_for_status()
        if response.json().get('success') is not True:
            raise ValueError('工厂返回进度推送失败')


class Keti5:
    def __init__(self, store):
        self.store = store
        self.finished_batches = set()
        self.lock = asyncio.Lock()

    async def progress(self, params, progress):
        if params is not None:
            try:
                await asyncio.to_thread(notify, params, progress)
            except Exception:
                logger.exception('keti5 进度推送失败 progress=%s', progress)

    async def complete(self, key, params):
        if params is None:
            return
        async with self.lock:
            if key in self.finished_batches:
                return
            for entry in self.store.entries(key[1], key[0]):
                if entry['timestamp'] != key[2]:
                    continue
                try:
                    metadata = Task._metadata(Task._task_dir(entry['task_id']))
                except TaskNotFoundError:
                    # 已删除的任务视为结束。
                    continue
                if metadata.get('verification_status', metadata['status']) not in TERMINAL:
                    return
            # 无论网络成功与否，每批只尝试一次，不自动重试。
            self.finished_batches.add(key)
            await self.progress(params, 100)

    async def task_finished(self, task_id, *, complete=True):
        try:
            metadata = Task._metadata(Task._task_dir(task_id))
            params = parameters(metadata.get('keti5'))
            if params is None:
                return
            cancelled = False
            try:
                await upload(task_id)
            except asyncio.CancelledError:
                cancelled = True
            except Exception:
                logger.exception('keti5 自动上传失败 task_id=%s', task_id)
            if complete:
                for entry in self.store.all_entries():
                    if entry['task_id'] == task_id:
                        await self.complete((entry['keti'], entry['projectID'], entry['timestamp']), params)
                        break
            if cancelled:
                raise asyncio.CancelledError

        except Exception:
            logger.exception('keti5 任务通知失败 task_id=%s', task_id)
