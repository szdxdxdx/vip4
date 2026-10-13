from ..config import VIP_ROOT

VIP_TASK_DIR = VIP_ROOT / 'tasks'
VIP_SKILL_DIR = VIP_ROOT / 'skills'
VIP_DATASET_DIR = VIP_ROOT / 'dataset' / '16-ip'

# 业务服务请求地址；部署地址变化时修改此处，重启后端生效。
KETI2_SEARCH_URL = 'http://8.130.30.48:8877/api/search/searchSoftwareIPByProjectId'
KETI2_DOWNLOAD_URL = 'http://8.130.30.48:8877/api/file/downloadFile'  # 空字符串禁用课题二路径下载。
KETI3_BASE_URL = 'http://127.0.0.1:50053'  # 课题三服务根地址，不含 /api；当前指向 server/tmp_keti3.py 临时后端。

PI_TOOLS = 'read,bash,edit,write,grep,find,ls'
PI_TIMEOUT = None  # 单次 Agent 执行时限，单位秒；None 表示不限时。
EVENT_POLL_INTERVAL = 0.05
MAX_SCAN_ENTRIES = 20000
MAX_WORKSPACE_FILES = 5000
