import json
import os
import subprocess
from pathlib import Path
from threading import Lock

import anyio

from .. import config


class PiAgent:
    def __init__(
        self,
        cwd: str | Path,
        session_dir: str | Path | None = None,
    ):
        self.cwd = Path(cwd).expanduser().resolve(strict=True)
        if (
            self.cwd.name != 'workspace'
            or self.cwd.parent.parent != config.VIP_TASK_DIR.resolve()
            or not self.cwd.is_dir()
        ):
            raise ValueError('Agent 工作目录必须是 tasks/<task_id>/workspace/')
        self.session_dir = (self.cwd.parent / 'session').resolve()
        if session_dir is not None and Path(session_dir).resolve() != self.session_dir:
            raise ValueError('Agent 会话目录必须是同一任务的 session/')
        self.session_dir.mkdir(parents=True, exist_ok=True)
        tmp_dir = self.cwd / 'tmp'
        tmp_dir.mkdir(exist_ok=True)

        if not config.VIP_SKILL_DIR.is_dir():
            raise FileNotFoundError(f'Skill 目录不存在：{config.VIP_SKILL_DIR}')

        self.process = subprocess.Popen(
            [
                'pi', 
                '--mode', 'rpc',
                '--tools', config.PI_TOOLS,
                '--no-extensions',
                '--no-approve',
                '--no-skills',
                '--skill', str(config.VIP_SKILL_DIR),
                '--no-prompt-templates',
                '--no-context-files',
                '--session-dir', str(self.session_dir),
                '--append-system-prompt', (
                    f'本轮软件 IP 验证工作目录只能是 {self.cwd}。'
                    f'所有输出和临时文件写入该目录，临时文件放在 {tmp_dir}。'
                    f'输入数据 {config.VIP_DATASET_DIR} 只读；'
                    f'允许读取 {config.VIP_SKILL_DIR} 中的 SKILL、参考文档，执行其脚本与已准备的虚拟环境。'
                    '不得读写其他任务或未指定的数据目录，不得修改原始 IP、SKILL 或全局环境。'
                    '按用户指定 SKILL 执行完整流程，不限制工具调用次数。'
                    '只有最终验证报告生成后才算任务完成，不得捏造工具结果。'
                    '完成任务后最终回复必须且只能是【任务已完成】，不得附带摘要、报告路径或其他文字。'
                    '若未完成或遇到无法继续的问题，必须如实说明，禁止回复【任务已完成】。'
                ),
            ],
            cwd=self.cwd,
            env={**os.environ, 'TMPDIR': str(tmp_dir), 'TMP': str(tmp_dir), 'TEMP': str(tmp_dir),
                 'PYTHONDONTWRITEBYTECODE': '1'},
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
