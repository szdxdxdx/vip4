import json
import subprocess
from pathlib import Path
from threading import Lock

import anyio

from .. import config


class PiAgent:
    def __init__(
        self,
        cwd: str | Path | None = None,
        session_dir: str | Path | None = None,
    ):
        self.session_dir = Path(session_dir if session_dir is not None else config.VIP_SESSION_DIR).expanduser().resolve()
        self.session_dir.mkdir(parents=True, exist_ok=True)

        if not config.VIP_SKILL_DIR.is_dir():
            raise FileNotFoundError(f'Skill 目录不存在：{config.VIP_SKILL_DIR}')

        self.process = subprocess.Popen(
            [
                'pi', 
                '--mode', 'rpc',
                '--tools', 'read',
                '--no-extensions',
                '--no-skills',
                '--skill', str(config.VIP_SKILL_DIR),
                '--no-prompt-templates',
                '--no-context-files',
                '--session-dir', str(self.session_dir),
            ],
            cwd=cwd if cwd is not None else config.PI_CWD,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        self._write_lock = Lock()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        with anyio.CancelScope(shield=True):
            await anyio.to_thread.run_sync(self.close)

    def close(self) -> None:
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.wait(timeout=config.PI_CLOSE_TIMEOUT)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.process.stdin.close()
        self.process.stdout.close()

    def send(self, jsonl: dict) -> None:
        with self._write_lock:
            self.process.stdin.write(json.dumps(jsonl, ensure_ascii=False).encode() + b'\n')
            self.process.stdin.flush()

    def send_prompt(self, prompt: str) -> None:
        self.send({'type': 'prompt', 'message': prompt})

    def receive(self) -> dict:
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError('Pi 进程已退出')
        return json.loads(line)
