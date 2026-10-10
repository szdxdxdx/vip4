import argparse
import asyncio
import json
from pathlib import Path

import anyio
import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pi_agent import PiAgent


class TalkRequest(BaseModel):
    text: str = Field(min_length=1, pattern=r"\S")


def create_app() -> FastAPI:
    app = FastAPI(title="VIP4")

    @app.post("/talk")
    async def talk(body: TalkRequest):
        async def stream():
            agent = None
            try:
                agent = PiAgent()
                async with asyncio.timeout(120):
                    await asyncio.to_thread(agent.send, {
                        "id": "talk", "type": "prompt", "message": body.text,
                    })
                    message = {}
                    while True:
                        event = await asyncio.to_thread(agent.receive)
                        if event.get("type") == "response" and event.get("id") == "talk":
                            if not event.get("success") or event.get("data", {}).get("disposition") == "handled":
                                raise RuntimeError("Pi 未接受对话请求")
                        elif event.get("type") == "message_end":
                            if event["message"].get("role") == "assistant":
                                message = event["message"]
                        elif event.get("type") == "agent_settled":
                            if event.get("aborted") or message.get("stopReason") not in ("stop", "length"):
                                raise RuntimeError("Pi 未能生成回复")
                        yield json.dumps(event, ensure_ascii=False) + "\n"
                        if event.get("type") == "agent_settled":
                            return
            except TimeoutError:
                yield json.dumps({"type": "error", "error": "LLM 回复超时"}) + "\n"
            except (OSError, RuntimeError, ValueError):
                yield json.dumps({"type": "error", "error": "Pi 调用失败，请检查模型配置"}) + "\n"
            finally:
                if agent is not None:
                    with anyio.CancelScope(shield=True):
                        await anyio.to_thread.run_sync(agent.close)

        return StreamingResponse(stream(), media_type="application/x-ndjson", headers={
            "Cache-Control": "no-cache", "X-Accel-Buffering": "no",
        })

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
