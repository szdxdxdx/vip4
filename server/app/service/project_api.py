"""项目验证 HTTP 接口，与现有任务接口共用无 /api 前缀的路径。"""
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ..vip_task.project import ProjectConflictError, ProjectNotFoundError
from .api import _read_task

router = APIRouter(prefix='/project')


class ProjectRequest(BaseModel):
    projectID: str = Field(min_length=1, pattern=r'\S')
    prompt: str | None = Field(default=None, min_length=1, pattern=r'\S')


@router.post('/create_project', status_code=202)
async def create_project(body: ProjectRequest, request: Request):
    try:
        return request.app.state.project_manager.submit(body.projectID, body.prompt)
    except ProjectConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


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
