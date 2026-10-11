import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import config
from ..agent.stream import agent_response

router = APIRouter()


class TaskRequest(BaseModel):
    task_id: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    prompt: str = Field(min_length=1, pattern=r"\S")



@router.post("/task")
async def task(body: TaskRequest):
    config.VIP_TASK_DIR.mkdir(parents=True, exist_ok=True)

    task_dir = config.VIP_TASK_DIR / body.task_id
    try:
        task_dir.mkdir()
    except FileExistsError:
        raise HTTPException(status_code=409, detail="task_id 已存在，请使用新的任务 ID") from None

    session_dir = task_dir / "session"
    workspace = task_dir / "workspace"
    for directory in (session_dir, workspace):
        directory.mkdir()

    metadata = {
        "task_id": body.task_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    (task_dir / "task.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    (task_dir / ".gitignore").write_text(
        "*\n", encoding="utf-8",
    )

    prompt = f"本轮对话的工作目录为 {workspace}，任务输出请放在该目录中。\n\n{body.prompt}"
    return agent_response(prompt, cwd=workspace, session_dir=session_dir)
