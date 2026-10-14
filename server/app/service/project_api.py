"""项目验证 HTTP 接口，与现有任务接口共用无 /api 前缀的路径。"""
import re
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field, model_validator

from ..vip_task.project import ProjectConflictError, ProjectNotFoundError
from .api import _read_task

router = APIRouter(prefix='/project')


class ProjectRequest(BaseModel):
    projectID: str = Field(min_length=1, pattern=r'\S')
    source: Literal['keti2', 'keti3'] = 'keti2'
    tool: Literal['CBMC', 'CPAchecker', 'KLEE'] = 'CBMC'
    userprompt: str | None = None

    @model_validator(mode='after')
    def validate_source_id(self):
        if self.source == 'keti3' and not re.fullmatch(r'[1-9][0-9]*', self.projectID):
            raise ValueError('课题三 projectID 必须是正整数的字符串')
        return self


@router.post('/create_project', status_code=202)
async def create_project(body: ProjectRequest, request: Request):
    try:
        return await request.app.state.project_manager.submit(
            body.projectID, body.userprompt, source=body.source, tool=body.tool)
    except ProjectConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from None


def _query(call, project_id: str, source: str):
    try:
        return _read_task(lambda: call(project_id, source=source))
    except ProjectNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None


@router.get('/get_progress')
async def get_progress(request: Request, projectID: str = Query(min_length=1, pattern=r'\S'),
                       source: Literal['keti2', 'keti3'] = Query()):
    return _query(request.app.state.project_manager.progress, projectID, source)


@router.get('/get_results')
async def get_results(request: Request, projectID: str = Query(min_length=1, pattern=r'\S'),
                       source: Literal['keti2', 'keti3'] = Query()):
    return _query(request.app.state.project_manager.results, projectID, source)
