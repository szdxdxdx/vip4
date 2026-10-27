import os
import json
from threading import RLock

from ..config import VIP_ROOT

VIP_TASK_DIR = VIP_ROOT / 'tasks'
VIP_SKILL_DIR = VIP_ROOT / 'skills'
VIP_DATASET_DIR = VIP_ROOT / 'dataset' / '16-ip'

# 业务服务默认值；持久化配置优先，保存后立即生效。
KETI2_BASE_URL = os.getenv("KETI2_BASE_URL", "http://8.130.30.48:8877")
KETI3_BASE_URL = os.getenv("KETI3_BASE_URL", "http://127.0.0.1:50053")
# KETI3_BASE_URL = 'http://192.128.190.250:50053'

# 课题五使用两个独立接口；填写实际完整地址，留空则报告配置缺失。
KETI5_CALLBACK_URL = os.getenv("KETI5_CALLBACK_URL", "http://127.0.0.1:10002/vip4-callback/notify")
KETI5_UPLOAD_URL = os.getenv("KETI5_UPLOAD_URL", "http://127.0.0.1:18086/sw/idep/plugin/reportUpload")
# 回调认证不用于文件上传；生产环境建议通过环境变量提供令牌。
KETI5_JENKINS_USER = os.getenv("KETI5_JENKINS_USER", "root")
KETI5_JENKINS_API_TOKEN = os.getenv("KETI5_JENKINS_API_TOKEN", "1110ab37a65c4dc381b48172ad75cd2856")
KETI5_TIMEOUT = float(os.getenv("KETI5_TIMEOUT", "30"))

EVENT_POLL_INTERVAL = 0.05
MAX_SCAN_ENTRIES = 20000
MAX_WORKSPACE_FILES = 5000


KETI_CONFIG_FILE = VIP_ROOT / 'keti-ip.json'
KETI_CONFIG_KEYS = (
    'KETI2_BASE_URL', 'KETI3_BASE_URL', 'KETI5_CALLBACK_URL',
    'KETI5_UPLOAD_URL', 'KETI5_JENKINS_USER', 'KETI5_JENKINS_API_TOKEN',
)
_keti_lock = RLock()


def get_keti_config():
    with _keti_lock:
        return {key: globals()[key] for key in KETI_CONFIG_KEYS}


def save_keti_config(values):
    with _keti_lock:
        # 先原子替换文件，再更新内存；写入失败不改变当前配置。
        temporary = KETI_CONFIG_FILE.with_suffix('.tmp')
        try:
            temporary.touch(mode=0o600, exist_ok=True)
            temporary.chmod(0o600)
            temporary.write_text(json.dumps(values, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            temporary.replace(KETI_CONFIG_FILE)
        finally:
            temporary.unlink(missing_ok=True)
        globals().update(values)


if KETI_CONFIG_FILE.exists():
    _saved = json.loads(KETI_CONFIG_FILE.read_text(encoding='utf-8'))
    if not isinstance(_saved, dict) or not all(
        key in KETI_CONFIG_KEYS and isinstance(value, str) for key, value in _saved.items()
    ):
        raise ValueError('keti-ip.json 必须为课题配置名称到字符串的 JSON 对象')
    globals().update(_saved)
