import argparse
from contextlib import asynccontextmanager

import uvicorn

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import config
from app.service.api import router as task_router
from app.vip_task.task_manager import TaskManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.task_manager = TaskManager()
    try:
        yield
    finally:
        await app.state.task_manager.close()


def create_app(backend_only: bool = False) -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.include_router(task_router)
    if not backend_only:
        app.mount("/", StaticFiles(directory=config.VIP_WEBUI_DIST_DIR, html=True))
    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default=config.HOST)
    parser.add_argument('--port', type=int, default=config.PORT)
    parser.add_argument('--backend-only', action='store_true')
    args = parser.parse_args()
    app = create_app(backend_only=args.backend_only)
    uvicorn.run(app, host=args.host, port=args.port)
