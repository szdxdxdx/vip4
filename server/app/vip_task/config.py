import os

from ..config import VIP_ROOT

VIP_TASK_DIR = VIP_ROOT / 'tasks'
VIP_SKILL_DIR = VIP_ROOT / 'skills'
VIP_DATASET_DIR = VIP_ROOT / 'dataset' / '16-ip'

# 业务服务请求地址；部署地址变化时修改此处，重启后端生效。
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
