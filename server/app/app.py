from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import config
from .task.api import router as task_router


def create_app() -> FastAPI:
    app = FastAPI()
    app.include_router(task_router)
    app.mount("/", StaticFiles(directory=config.VIP_WEBUI_DIST_DIR, html=True))
    return app
