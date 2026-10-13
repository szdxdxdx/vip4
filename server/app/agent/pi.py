import asyncio
import uuid
import json
import logging
import subprocess
from collections.abc import Sequence
from pathlib import Path
from threading import Lock

import anyio

from . import config


logger = logging.getLogger(__name__)


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
        self.events = asyncio.Queue()
        self.responses = {}
        self.settled = False
        self.reader = None
        self.closing = False
        logger.info('Pi 进程启动 pid=%s cwd=%s', self.process.pid, self.cwd)

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
        # 关闭 stdin 请求正常退出；逾期才发送信号，始终等待进程回收。
        with self._write_lock:
            if not self.process.stdin.closed:
                try:
                    self.process.stdin.close()
                except BrokenPipeError:
                    pass
        try:
            self.process.wait(timeout=self.close_timeout)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:
                self.process.wait(timeout=self.close_timeout)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process.stdout.close()
        logger.info('Pi 进程已释放 pid=%s returncode=%s', self.process.pid, self.process.returncode)

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

    async def start_reader(self):
        if self.reader is not None:
            return
        # 唯一 stdout 消费者，响应按 ID 分发，事件按原顺序入队。
        async def pump():
            try:
                while True:
                    record = await asyncio.to_thread(self.receive)
                    if record.get('type') == 'response':
                        future = self.responses.get(record.get('id'))
                        if future is not None and not future.done():
                            if record.get('success'):
                                future.set_result(record.get('data', {}))
                            else:
                                future.set_exception(RuntimeError(record.get('error', 'RPC 请求失败')))
                    else:
                        if record.get('type') == 'agent_start':
                            self.settled = False
                        if record.get('type') == 'agent_settled':
                            self.settled = True
                        await self.events.put(record)
            except Exception as error:
                for future in self.responses.values():
                    if not future.done():
                        future.set_exception(error)
                if not self.closing and not self.settled:
                    await self.events.put({'type': 'error', 'error': str(error)})
        self.reader = asyncio.create_task(pump())

    async def rpc(self, command, **fields):
        request_id = uuid.uuid4().hex
        future = asyncio.get_running_loop().create_future()
        self.responses[request_id] = future
        try:
            await asyncio.to_thread(self.send, {'id': request_id, 'type': command, **fields})
            return await asyncio.wait_for(future, 30)
        finally:
            self.responses.pop(request_id, None)

    async def abort(self):
        try:
            await self.rpc('clear_queue')
        finally:
            await self.rpc('abort')

    async def stop_reader(self):
        self.closing = True
        await asyncio.to_thread(self.close)
        if self.reader is not None:
            await asyncio.gather(self.reader, return_exceptions=True)
