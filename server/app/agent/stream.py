import asyncio
from pathlib import Path

from .. import config
from .pi_agent import PiAgent


async def agent_events(prompt: str, cwd: Path, session_dir: Path):
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
                yield event
                if event.get("type") == "agent_settled":
                    return
    except TimeoutError:
        yield {"type": "error", "error": "LLM 回复超时"}
    except (OSError, RuntimeError, ValueError):
        yield {"type": "error", "error": "Pi 调用失败，请检查模型配置"}
