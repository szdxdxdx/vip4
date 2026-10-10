import argparse
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


class TalkRequest(BaseModel):
    text: str = Field(min_length=1)


def create_app() -> FastAPI:
    app = FastAPI(title="VIP4")

    @app.post("/talk")
    def talk(body: TalkRequest):
        return {"text": body.text}

    webui_dir = Path(__file__).resolve().parent.parent / "webui" / "dist"
    app.mount("/", StaticFiles(directory=webui_dir, html=True))

    return app

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8414)
    args = parser.parse_args()
    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
