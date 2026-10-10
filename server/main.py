import argparse
import asyncio
import json

import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import config
from pi_agent import PiAgent


class TalkRequest(BaseModel):
    text: str = Field(min_length=1, pattern=r"\S")


def create_app() -> FastAPI:
    app = FastAPI()

    @app.post("/talk")
    async def talk(body: TalkRequest):
        async def stream():
            try:
                async with PiAgent() as agent, asyncio.timeout(config.PI_TIMEOUT):
                    await asyncio.to_thread(agent.send_prompt, body.text)
                    message = {}
                    while True:
                        event = await asyncio.to_thread(agent.receive)
                        if event.get("type") == "response" and event.get("command") == "prompt":
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

        return StreamingResponse(stream(), media_type="application/x-ndjson", headers={
            "Cache-Control": "no-cache", "X-Accel-Buffering": "no",
        })

    app.mount("/", StaticFiles(directory=config.VIP_WEBUI_DIST_DIR, html=True))

    return app

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default=config.HOST)
    parser.add_argument('--port', type=int, default=config.PORT)
    args = parser.parse_args()
    app = create_app()
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == '__main__':
    main()
