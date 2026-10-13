"""项目验证 HTTP 接口，与现有任务接口共用无 /api 前缀的路径。"""
import re
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field, model_validator

from ..vip_task.project import ProjectConflictError, ProjectNotFoundError
from ..vip_task.task import TaskDeletingError, TaskPathError
from .api import _read_task

router = APIRouter(prefix='/project')


class ProjectDeleteRequest(BaseModel):
    projectID: str = Field(min_length=1, pattern=r'\S')


class ProjectRequest(ProjectDeleteRequest):
    source: Literal['keti2', 'keti3'] = 'keti2'
    prompt: str | None = Field(default=None, min_length=1, pattern=r'\S')
    force: bool = False

    @model_validator(mode='after')
    def validate_source_id(self):
        if self.source == 'keti3' and not re.fullmatch(r'[1-9][0-9]*', self.projectID):
            raise ValueError('课题三 projectID 必须是正整数的字符串')
        return self


@router.post('/create_project', status_code=202)
async def create_project(body: ProjectRequest, request: Request):
    try:
        return await request.app.state.project_manager.submit(
            body.projectID, body.prompt, force=body.force, source=body.source)
    except (ProjectConflictError, TaskDeletingError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None
    except TaskPathError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from None
    except PermissionError:
        raise HTTPException(status_code=403, detail='强制提交失败：无权删除旧任务文件') from None
    except OSError:
        raise HTTPException(status_code=500, detail='强制提交失败：旧任务未完整删除，请重试') from None


@router.post('/delete_project')
async def delete_project(body: ProjectDeleteRequest, request: Request):
    try:
        return await request.app.state.project_manager.delete(body.projectID)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    except (ProjectConflictError, TaskDeletingError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except TaskPathError as error:
        raise HTTPException(status_code=error.status_code, detail=str(error)) from None
    except PermissionError:
        raise HTTPException(status_code=403, detail='项目删除失败：无权删除任务文件') from None
    except OSError:
        raise HTTPException(status_code=500, detail='项目删除失败：任务未完整删除，请重试') from None


def _query(call, project_id: str):
    try:
        return _read_task(call, project_id)
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@router.get('/get_progress')
async def get_progress(request: Request, projectID: str = Query(min_length=1, pattern=r'\S')):
    return _query(request.app.state.project_manager.progress, projectID)


@router.get('/get_results')
async def get_results(request: Request, projectID: str = Query(min_length=1, pattern=r'\S')):
    return _query(request.app.state.project_manager.results, projectID)
