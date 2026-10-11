from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config
from .task.api import router as task_router
from .task.service import TaskManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.task_manager = TaskManager()
    try:
        yield
    finally:
        await app.state.task_manager.close()


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.include_router(task_router)
    app.mount("/", StaticFiles(directory=config.VIP_WEBUI_DIST_DIR, html=True))
    return app
