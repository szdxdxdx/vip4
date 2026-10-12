import json
import subprocess
from collections.abc import Sequence
from pathlib import Path
from threading import Lock

import anyio

from . import config


class PiAgent:
    def __init__(
        self,
        cwd: str | Path,
        session_dir: str | Path | None = None,
        *,
        argv: Sequence[str] | None = None,
        env: dict[str, str] | None = None,
        close_timeout: float | None = config.PI_CLOSE_TIMEOUT,
    ):
        self.cwd = Path(cwd)
        self.session_dir = Path(session_dir) if session_dir is not None else None
        self.close_timeout = close_timeout
        command = list(argv) if argv is not None else [config.PI_EXECUTABLE, '--mode', 'rpc']
        if self.session_dir is not None:
            command.extend(['--session-dir', str(self.session_dir)])
        self.process = subprocess.Popen(
            command, cwd=self.cwd, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
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

    def is_running(self) -> bool:
        return self.process.poll() is None

    def close(self) -> None:
        if self.is_running():
            self.process.terminate()
        try:
            self.process.wait(timeout=self.close_timeout)
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
