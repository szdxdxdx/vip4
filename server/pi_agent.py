import json
import subprocess
from pathlib import Path
from threading import Lock


class PiAgent:
    """Pi RPC 进程。send 写入一条 JSONL，receive 阻塞读取一条事件；只允许一个读取者。"""

    def __init__(self, cwd: str | Path | None = None):
        self.process = subprocess.Popen(
            ['pi', '--mode', 'rpc', '--no-session', '--no-tools',
             '--no-extensions', '--no-skills', '--no-prompt-templates', '--no-context-files'],
            cwd=cwd or Path(__file__).resolve().parent,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        self._write_lock = Lock()

    def send(self, jsonl: dict | str) -> None:
        """接受 JSON 对象或单条 JSONL 字符串，自动添加换行并 flush。"""
        command = json.loads(jsonl) if isinstance(jsonl, str) else jsonl
        if not isinstance(command, dict):
            raise ValueError('RPC 命令必须是 JSON 对象')
        with self._write_lock:
            self.process.stdin.write(json.dumps(command, ensure_ascii=False).encode() + b'\n')
            self.process.stdin.flush()

    def receive(self) -> dict:
        """读取 stdout 的下一条 JSONL；stderr 保留为后端日志。"""
        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError('Pi 进程已退出')
        return json.loads(line)

    def close(self) -> None:
        """终止进程，解除阻塞读取，释放管道。"""
        if self.process.poll() is None:
            self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.process.stdin.close()
        self.process.stdout.close()
