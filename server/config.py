from pathlib import Path

VIP_ROOT = Path(__file__).resolve().parents[1]
VIP_SERVER_DIR     = VIP_ROOT / 'server'
VIP_WEBUI_DIST_DIR = VIP_ROOT / 'webui' / 'dist'
VIP_SKILL_DIR      = VIP_ROOT / 'skills'
VIP_SESSION_DIR    = VIP_ROOT / 'sessions'
VIP_TASK_DIR       = VIP_ROOT / 'tasks'
VIP_DATASET_DIR    = VIP_ROOT / 'dataset' / '16-ip'

HOST = '127.0.0.1'
PORT = 8414

PI_TOOLS = 'read,bash,edit,write,grep,find,ls'
PI_TIMEOUT = None
PI_CLOSE_TIMEOUT = 5

# TODO 整个项目的全局配置放在这里
# 各个模块内的配置应该另建 config.py
