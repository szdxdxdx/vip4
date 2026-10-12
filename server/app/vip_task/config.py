from ..config import VIP_ROOT

VIP_TASK_DIR = VIP_ROOT / 'tasks'
VIP_SKILL_DIR = VIP_ROOT / 'skills'
VIP_DATASET_DIR = VIP_ROOT / 'dataset' / '16-ip'

PI_TOOLS = 'read,bash,edit,write,grep,find,ls'
PI_TIMEOUT = None  # 单次 Agent 执行时限，单位秒；None 表示不限时。
EVENT_POLL_INTERVAL = 0.05
MAX_SCAN_ENTRIES = 20000
MAX_WORKSPACE_FILES = 5000
