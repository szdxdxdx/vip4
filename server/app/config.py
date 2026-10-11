from pathlib import Path

VIP_ROOT = Path(__file__).resolve().parents[2]
VIP_SERVER_DIR = VIP_ROOT / 'server'
VIP_WEBUI_DIST_DIR = VIP_ROOT / 'webui' / 'dist'
VIP_SKILL_DIR = VIP_ROOT / 'skills'
VIP_SESSION_DIR = VIP_ROOT / 'sessions'
VIP_TASK_DIR = VIP_ROOT / 'tasks'
VIP_DATASET_DIR = VIP_ROOT / 'dataset' / '16-ip'

HOST = '127.0.0.1'
PORT = 8414

PI_TOOLS = 'read,bash,edit,write,grep,find,ls'
PI_TIMEOUT = None  # 完整验证流程不设总时限；每个验证 case 由 SKILL 设置超时
PI_CLOSE_TIMEOUT = 5
