"""后端 UTC 批次时间；同一进程内严格递增，避免并发串批。"""
from datetime import datetime, timedelta, timezone
from threading import Lock

HISTORICAL_TIMESTAMP = '2026-10-14 00:00:00'
_lock = Lock()
_last = datetime.min.replace(tzinfo=timezone.utc)


def new_timestamp() -> str:
    global _last
    with _lock:
        _last = max(datetime.now(timezone.utc), _last + timedelta(microseconds=1))
        return _last.strftime('%Y-%m-%d %H:%M:%S.%f')
