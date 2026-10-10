from pathlib import Path

VIP_ROOT = Path(__file__).resolve().parent.parent
VIP_SERVER_DIR = VIP_ROOT / 'server'
VIP_WEBUI_DIST_DIR = VIP_ROOT / 'webui' / 'dist'
VIP_SKILL_DIR = VIP_ROOT / 'skills'
VIP_SESSION_DIR = VIP_ROOT / 'sessions'

HOST = '127.0.0.1'
PORT = 8414

PI_CWD = VIP_SERVER_DIR
PI_TIMEOUT = 120
PI_CLOSE_TIMEOUT = 5
