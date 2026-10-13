import json
import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path


def message_text(content) -> str:
    # RPC user 内容既可为字符串，也可为 text/image 内容块。
    if isinstance(content, str):
        return content
    return ''.join(block.get('text', '') for block in content
                   if isinstance(block, dict) and block.get('type') == 'text'
                   and isinstance(block.get('text'), str)) if isinstance(content, list) else ''


def prompt_key(content) -> str:
    text = message_text(content)
    skill = re.match(r'<skill name="([^"]+)" location="[^"]*">\n', text)
    if skill:
        end = text.rfind('\n</skill>\n\n')
        if end != -1:
            text = '/skill:' + skill[1] + ' ' + text[end + len('\n</skill>\n\n'):]
    return text.strip()


@dataclass
class SessionHistory:
    prompt: str = ''
    events: list[dict] = field(default_factory=list)


def read_history(task_dir: Path, skill_file: Path) -> SessionHistory:
    history = SessionHistory()
    directory_fd = session_fd = None
    try:
        # 目录句柄限定读取边界，拒绝符号链接，避免检查后替换。
        directory_fd = os.open(task_dir, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            session_fd = os.open('pi_session', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                 dir_fd=directory_fd)
        except FileNotFoundError:
            return history
        candidates = []
        with os.scandir(session_fd) as files:
            for file in files:
                if file.name.endswith('.jsonl') and file.is_file(follow_symlinks=False):
                    candidates.append((file.stat(follow_symlinks=False).st_mtime_ns, file.name))
        if not candidates:
            return history
        name = max(candidates)[1]
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=session_fd)
        entries = {}
        leaf = None
        damaged = False
        with os.fdopen(fd, 'r', encoding='utf-8', errors='replace') as source:
            if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                raise ValueError
            for line in source:
                try:
                    entry = json.loads(line)
                    if not isinstance(entry, dict) or not isinstance(entry.get('type'), str):
                        raise ValueError
                    if entry['type'] == 'session':
                        continue
                    entry_id, parent = entry.get('id'), entry.get('parentId')
                    if (not isinstance(entry_id, str) or not entry_id or entry_id in entries
                            or 'parentId' not in entry
                            or (parent is not None and (not isinstance(parent, str) or parent not in entries))):
                        raise ValueError
                    if entry['type'] == 'message':
                        message = entry.get('message')
                        if not isinstance(message, dict) or not isinstance(message.get('role'), str):
                            raise ValueError
                        if not isinstance(message.get('content'), (str, list)):
                            raise ValueError
                    entries[entry_id] = entry
                    leaf = entry_id
                except (ValueError, TypeError):
                    damaged = True

        # 展示原始分支全路径，不用压缩摘要或 context_edit 改写对话。
        branch = []
        while leaf is not None:
            entry = entries[leaf]
            branch.append(entry)
            leaf = entry['parentId']
        first_user = True
        for entry in reversed(branch):
            if entry['type'] != 'message':
                continue
            message = entry['message']
            role, content = message['role'], message['content']
            if role == 'user' and first_user:
                first_user = False
                text = content if isinstance(content, str) else ''.join(
                    block['text'] for block in content
                    if isinstance(block, dict) and block.get('type') == 'text'
                    and isinstance(block.get('text'), str)
                )
                workspace_prefix = f'工作目录为 {task_dir / "workspace"}\n\n'
                skill_prefix = f'<skill name="verify-ip" location="{skill_file}">\n'
                if text.startswith(skill_prefix):
                    end = text.find('\n</skill>\n\n', len(skill_prefix))
                    if end != -1 and text[end + len('\n</skill>\n\n'):].startswith(workspace_prefix):
                        text = text[end + len('\n</skill>\n\n'):]
                if text.startswith(workspace_prefix):
                    text = text[len(workspace_prefix):]
                history.prompt = text
                history.events.append({'type': 'user', 'message': text})
            elif role == 'user':
                history.events.append({'type': 'user', 'message': message_text(content)})
            elif role == 'assistant':
                history.events.append({'type': 'agent', 'data': {
                    'type': 'message_end', 'message': message,
                }})
                for block in content if isinstance(content, list) else []:
                    if (isinstance(block, dict) and block.get('type') == 'toolCall'
                            and isinstance(block.get('id'), str) and isinstance(block.get('name'), str)):
                        history.events.append({'type': 'agent', 'data': {
                            'type': 'tool_execution_start', 'toolCallId': block['id'],
                            'toolName': block['name'], 'args': block.get('arguments', {}),
                        }})
            elif role == 'toolResult':
                history.events.append({'type': 'agent', 'data': {
                    'type': 'tool_execution_end', 'toolCallId': message.get('toolCallId'),
                    'toolName': message.get('toolName'), 'result': message,
                    'isError': message.get('isError', True),
                }})
        if damaged:
            history.events.append({'type': 'error', 'error': 'Pi 会话含损坏记录，已跳过；历史可能不完整'})
    except (OSError, ValueError):
        history.events.append({'type': 'error', 'error': '无法安全读取本任务 Pi 会话历史'})
    finally:
        if session_fd is not None:
            os.close(session_fd)
        if directory_fd is not None:
            os.close(directory_fd)
    return history
