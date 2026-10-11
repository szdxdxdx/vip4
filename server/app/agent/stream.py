import asyncio
import json
from pathlib import Path

from fastapi.responses import StreamingResponse

from .. import config
from .pi_agent import PiAgent


def agent_response(prompt: str, cwd: Path | None = None, session_dir: Path | None = None):
    async def stream():
        try:
            async with PiAgent(cwd=cwd, session_dir=session_dir) as agent, asyncio.timeout(config.PI_TIMEOUT):
                await asyncio.to_thread(agent.send_prompt, prompt)
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

