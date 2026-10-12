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


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.include_router(task_router)
    app.mount("/", StaticFiles(directory=config.VIP_WEBUI_DIST_DIR, html=True))
    return app


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default=config.HOST)
    parser.add_argument('--port', type=int, default=config.PORT)
    args = parser.parse_args()
    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port)
