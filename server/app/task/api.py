from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .service import TaskExistsError, TaskNotFoundError

router = APIRouter()


class TaskRequest(BaseModel):
    task_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    prompt: str = Field(min_length=1, pattern=r"\S")


@router.post('/task/create_task', status_code=201)
async def create_task(body: TaskRequest, request: Request):
    try:
        return request.app.state.task_manager.create_task(body.task_id, body.prompt)
    except TaskExistsError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.get('/task/get_events')
async def get_events(request: Request, task_id: str = Query(
    max_length=64, pattern=r'^[a-zA-Z0-9][a-zA-Z0-9_-]*$',
)):
    try:
        events = request.app.state.task_manager.get_events(task_id)
    except TaskNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from None
    return StreamingResponse(events, media_type='application/x-ndjson', headers={
        'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no',
    })
