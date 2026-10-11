from datetime import datetime
from pathlib import Path
import re


DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
CASE_NAME_PATTERN = re.compile(r"case(_nf)?(_\d+)?((_R|_S)(_\d+))*")


def check_case_name(case_name: str):
    if not CASE_NAME_PATTERN.fullmatch(case_name):
        raise ValueError(f"case 名称不符合要求：{case_name!r}")


def is_nonfunctional_case(name: str) -> bool:
    check_case_name(name)
    return name.startswith("case_nf")


def current_datetime() -> datetime:
    return datetime.now()


def format_datetime(value: datetime) -> str:
    return value.strftime(DATETIME_FORMAT)


def current_datetime_str() -> str:
    return format_datetime(current_datetime())


def parse_datetime(value: str) -> datetime:
    return datetime.strptime(value, DATETIME_FORMAT)


def elapsed_seconds(start: int | float | datetime, end: int | float | datetime) -> int:
    assert isinstance(start, (int | float, datetime))
    assert isinstance(end, (int | float, datetime))

    if isinstance(start, datetime) and isinstance(end, datetime):
        seconds = (end - start).total_seconds()
    else:
        seconds = float(end) - float(start)
    return int(max(0, seconds))


def ensure_output_dir(output_dir: Path):
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        return
    if not output_dir.is_dir():
        raise ValueError(f"路径指向了一个文件，而不是目录 {output_dir}")
    if any(output_dir.iterdir()):
        raise ValueError(f"目录已存在且不为空 {output_dir}")
