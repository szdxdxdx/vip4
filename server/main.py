import argparse
import logging
from time import perf_counter
from contextlib import asynccontextmanager

import uvicorn

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.service import config
from app.service.api import router as task_router
from app.service.project_api import router as project_router
from app.service.config_api import router as config_router
from app.vip_task.task_manager import TaskManager
from app.vip_task.project import ProjectManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.task_manager = TaskManager()
    try:
        app.state.project_manager = ProjectManager(app.state.task_manager)
        try:
            yield
        finally:
            await app.state.project_manager.close()
    finally:
        await app.state.task_manager.close()


def create_app(backend_only: bool = False) -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    app.include_router(task_router)
    app.include_router(project_router)
    app.include_router(config_router)

    @app.middleware('http')
    async def log_request(request, call_next):
        started = perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            # 不记录查询参数、请求正文及提示词。
            logger.info('HTTP %s %s status=%s duration_ms=%.1f',
                        request.method, request.url.path, status,
                        (perf_counter() - started) * 1000)

    if not backend_only:
        @app.get('/config/pi-models', include_in_schema=False)
        async def pi_models_page():
            return FileResponse(config.VIP_WEBUI_DIST_DIR / 'index.html')

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
