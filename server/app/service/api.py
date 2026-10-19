from starlette.background import BackgroundTask
from ..vip_task.archive import task_archive
from typing import Literal
from ..vip_task.inputs import create_local, dataset_list
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from ..vip_task.task import (
    TaskExistsError,
    TaskConflictError,
    TaskDeletingError,
    TaskNotFoundError,
    TaskPathError,
    TaskMetadataError,
    TaskReadLimitError,
)

router = APIRouter()


class TaskRequest(BaseModel):
    ip_name: str = Field(min_length=1, max_length=128, pattern=r'^[^/\\]+$')
    tool: Literal['CBMC', 'CPAchecker', 'KLEE']
    userprompt: str | None = None


@router.get('/task/list_dataset')
def list_dataset():
    return dataset_list()


@router.post('/task/create_task', status_code=201)
async def create_task(body: TaskRequest, request: Request):
    try:
        return await create_local(request.app.state.task_manager, request.app.state.project_manager.store,
                                  body.ip_name, body.tool, body.userprompt)
    except ValueError as error:
        raise HTTPException(400, str(error)) from None
    except (TaskExistsError, TaskDeletingError) as error:
        raise HTTPException(409, str(error)) from None


@router.delete('/task/delete_task')
async def delete_task(
    request: Request,
    task_id: str = Query(max_length=64, pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$'),
):
    try:
        return await request.app.state.task_manager.delete_task(task_id)
    except TaskDeletingError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except TaskNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except TaskPathError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from None
    except PermissionError:
        raise HTTPException(status_code=403, detail='任务未完整删除：无权删除任务文件') from None
    except OSError:
        raise HTTPException(status_code=500, detail='任务未完整删除：无法删除任务文件') from None


@router.get('/task/get_events')
async def get_events(
    request: Request,
    task_id: str = Query(
        max_length=64,
        pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$',
    ),
):
    try:
        events = request.app.state.task_manager.get_events(task_id)
    except TaskNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    return StreamingResponse(events, media_type='application/x-ndjson', headers={
        'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no',
    })


def _read_task(call, *args):
    try:
        return call(*args)
    except TaskNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except TaskPathError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from None
    except TaskReadLimitError as error:
        raise HTTPException(status_code=413, detail=str(error)) from None
    except PermissionError:
        raise HTTPException(status_code=403, detail='无权读取任务文件') from None
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail='任务文件不存在') from None
    except (TaskMetadataError, OSError):
        raise HTTPException(status_code=500, detail='无法读取任务数据') from None


@router.get('/task/list_tasks')
async def list_tasks(request: Request, projectID: str | None = None, task_id: str | None = None,
                     keti: Literal['keti2', 'keti3'] | None = None):
    return _read_task(request.app.state.task_manager.list_tasks, projectID, task_id, keti)


@router.get('/task/get_task')
def get_task(
    request: Request,
    task_id: str = Query(max_length=64, pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$'),
):
    return _read_task(request.app.state.task_manager.get_task, task_id)


@router.get('/task/get_file')
def get_file(
    request: Request,
    task_id: str = Query(max_length=64, pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$'),
    path: str = Query(min_length=1),
    download: bool = False
):
    file = _read_task(request.app.state.task_manager.get_file, task_id, path)
    headers = {'X-Content-Type-Options': 'nosniff'}
    if file.kind == 'report_html':
        headers['Content-Security-Policy'] = 'sandbox allow-scripts'
    return FileResponse(
        file.path, media_type=file.media_type, filename=file.path.name,
        content_disposition_type='attachment' if download or file.attachment else 'inline',
        headers=headers,
    )


class ChatTaskRequest(BaseModel):
    task_id: str


class SendMessageRequest(ChatTaskRequest):
    message: str


async def _chat_call(call, *args):
    try:
        return await call(*args)
    except (TaskConflictError, TaskDeletingError) as error:
        raise HTTPException(409, str(error)) from None
    except TaskNotFoundError as error:
        raise HTTPException(404, str(error)) from None
    except TaskPathError as error:
        raise HTTPException(error.status_code, str(error)) from None
    except (ValueError, TaskMetadataError, OSError) as error:
        raise HTTPException(400, str(error)) from None


@router.post('/task/send_message', status_code=202)
async def send_message(body: SendMessageRequest, request: Request):
    return await _chat_call(request.app.state.task_manager.send_message, body.task_id, body.message)


@router.post('/task/pause_task')
async def pause_task(body: ChatTaskRequest, request: Request):
    return await _chat_call(request.app.state.task_manager.pause_task, body.task_id)


@router.get('/task/download_task')
def download_task(task_id: str = Query(max_length=64, pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$')):
    archive = _read_task(task_archive, task_id)
    return FileResponse(archive, media_type='application/zip', filename=f'{task_id}.zip',
                        background=BackgroundTask(archive.unlink, missing_ok=True))


@router.post('/task/upload_to_factory')
async def upload_to_factory(task_id: str = Query(max_length=64, pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$')):
    from ..vip_task.keti5 import parameters, upload
    from ..vip_task.task import Task
    metadata = _read_task(lambda: Task._metadata(Task._task_dir(task_id)))
    if parameters(metadata.get('keti5')) is None:
        raise HTTPException(400, '此任务没有 keti5 参数，无法上传')
    try:
        await upload(task_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(502, '上传到工厂失败，请检查服务配置或稍后重传') from None
    return {'success': True}
