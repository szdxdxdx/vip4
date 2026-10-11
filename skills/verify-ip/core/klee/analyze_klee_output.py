"""从 KLEE 原始输出中提取关键信息。

负责解析 KLEE 运行产生的原始输出（info、messages.txt、warnings.txt、run.stats、*.err 文件），
提取宏观统计信息，供 run_klee.py 生成 result.json、make_report.py 生成 report.json/report.html 使用。

详细内容（完整错误原文、工具信息、标准错误）保留在 KLEE 原始输出文件中，
本模块只提取摘要级别的数据。
"""
import re
import sqlite3
from pathlib import Path


# KLEE .err 文件后缀与错误类型的映射
_ERR_TYPE_PATTERNS = [
    ("ptr", ".ptr.err"),
    ("assert", ".assert.err"),
    ("div", ".div.err"),
    ("overflow", ".overflow.err"),
    ("external", ".external.err"),
    ("user", ".user.err"),
    ("free", ".free.err"),
]

# run.stats 中路径终止原因字段与简洁键名的映射
_TERMINATION_MAP = [
    ("exit", "TerminationExit"),
    ("early", "TerminationEarly"),
    ("solver_error", "TerminationSolverError"),
    ("program_error", "TerminationProgramError"),
    ("user_error", "TerminationUserError"),
    ("execution_error", "TerminationExecutionError"),
    ("early_algorithm", "TerminationEarlyAlgorithm"),
    ("early_user", "TerminationEarlyUser"),
]

# 警告类型判定关键字
_WARNING_TYPE_KEYWORDS = [
    ("concretizing", "concretizing"),
    ("external", "external"),
]


def _read_text(path: Path | None) -> str:
    """读取文本文件，失败时返回空字符串。"""
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _load_stats_row(klee_output_dir: Path | None) -> dict | None:
    """读取 run.stats（SQLite）中最新一行的统计字段。

    KLEE 的 run.stats 为 SQLite 数据库，每行记录一次采样；
    取 Instructions 最大的一行作为最终统计。读取失败时返回 None。
    """
    if klee_output_dir is None:
        return None
    stats_path = klee_output_dir / "run.stats"
    if not stats_path.is_file():
        return None
    try:
        conn = sqlite3.connect(f"file:{stats_path}?mode=ro", uri=True)
        try:
            cursor = conn.execute(
                "SELECT * FROM stats ORDER BY Instructions DESC LIMIT 1"
            )
            col_names = [d[0] for d in cursor.description]
            row = cursor.fetchone()
            if row is None:
                return None
            return dict(zip(col_names, row))
        finally:
            conn.close()
    except (sqlite3.Error, OSError):
        return None


def load_klee_output(*, klee_output_dir: Path | None, stdout_path: Path | None = None,
                     stderr_path: Path | None = None) -> dict:
    """加载 KLEE 原始输出，返回结构化数据。

    参数：
    - klee_output_dir: KLEE 的 --output-dir 目录（含 info、messages.txt、warnings.txt、run.stats、*.err）
    - stdout_path: KLEE 标准输出文件路径（可选）
    - stderr_path: KLEE 标准错误文件路径（可选）

    返回：
    {
        "info": <str>,          # info 文件内容
        "messages": <str>,      # messages.txt 内容
        "warnings": <str>,      # warnings.txt 内容
        "stdout": <str>,        # 标准输出内容
        "stderr": <str>,        # 标准错误内容
        "err_files": [<str>],   # .err 错误文件名列表（相对 klee_output_dir）
        "stats_row": null | <dict>,  # run.stats 最新一行（键为 stats 表字段名）
    }
    """
    info_text = ""
    messages_text = ""
    warnings_text = ""
    err_files: list[str] = []
    stats_row = None
    if klee_output_dir is not None:
        info_text = _read_text(klee_output_dir / "info")
        messages_text = _read_text(klee_output_dir / "messages.txt")
        warnings_text = _read_text(klee_output_dir / "warnings.txt")
        stats_row = _load_stats_row(klee_output_dir)
        try:
            err_files = sorted(
                p.name for p in klee_output_dir.glob("*.err")
            )
        except OSError:
            err_files = []

    return {
        "info": info_text,
        "messages": messages_text,
        "warnings": warnings_text,
        "stdout": _read_text(stdout_path),
        "stderr": _read_text(stderr_path),
        "err_files": err_files,
        "stats_row": stats_row,
    }


def extract_conclusion(data: dict, *, timed_out: bool) -> str:
    """提取 KLEE 验证结论。

    KLEE 自身不输出 "验证通过/不通过" 的结论，只报告其执行状态。
    这里根据 KLEE 原始输出中的证据，描述工具执行是否正常完成。

    规则：
    - 超时 → TIMEOUT
    - 统计信息不完整（无 KLEE: done: 行）→ INCOMPLETE（异常中断）
    - 存在非 user 类型的 .err 文件 → ERRORS（完成但发现错误）
    - 其他 → COMPLETED（正常完成，未发现错误）

    这四个值描述的是工具的执行结果，不代表"验证通过/不通过"的判断。
    验证结论的判断应交给 AI Agent（ai_agent_conclusion 字段）。
    """
    if timed_out:
        return "TIMEOUT"
    statistics = extract_statistics(data)
    if statistics is None:
        return "INCOMPLETE"
    if error_counts(data)["total"] > 0:
        return "ERRORS"
    return "COMPLETED"


def extract_statistics(data: dict) -> dict | None:
    """从 info 和 run.stats 中提取 KLEE 执行统计。

    基础统计解析 "KLEE: done: xxx = N" 形式的行；
    覆盖率、路径终止原因、外部调用次数从 run.stats 提取。
    基础统计不完整时返回 None。
    """
    info_text = data.get("info", "")
    if not info_text:
        return None

    values = {}
    patterns = {
        "explored_paths": r"KLEE: done: explored paths = (\d+)",
        "completed_paths": r"KLEE: done: completed paths = (\d+)",
        "generated_tests": r"KLEE: done: generated tests = (\d+)",
        "total_instructions": r"KLEE: done: total instructions = (\d+)",
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, info_text)
        if match:
            values[key] = int(match.group(1))

    # 基础统计不完整（如超时中断）时返回 None
    if len(values) != len(patterns):
        return None

    # 从 run.stats 提取覆盖率、终止原因、外部调用
    stats_row = data.get("stats_row")
    coverage = None
    termination_reasons = None
    external_calls = None
    if stats_row:
        covered = stats_row.get("CoveredInstructions")
        uncovered = stats_row.get("UncoveredInstructions")
        if covered is not None and uncovered is not None:
            total = covered + uncovered
            percentage = round(covered / total * 100, 1) if total > 0 else None
            coverage = {
                "covered_instructions": covered,
                "uncovered_instructions": uncovered,
                "percentage": percentage,
            }

        reasons = {}
        for key, field in _TERMINATION_MAP:
            reasons[key] = stats_row.get(field, 0)
        termination_reasons = reasons

        external_calls = stats_row.get("ExternalCalls")

    values["coverage"] = coverage
    values["termination_reasons"] = termination_reasons
    values["external_calls"] = external_calls
    return values


def extract_warnings(data: dict) -> dict | None:
    """从 warnings.txt 中提取警告信息。

    按 "KLEE: WARNING" 条目切分（一条警告可能跨行），
    统计总数与具体化（silently concretizing）警告数。

    返回：
    {
        "total": <int>,
        "concretizing": <int>,
        "items": [{"type": <str>, "message": <str>}]
    }
    """
    warnings_text = data.get("warnings", "")
    blocks = [
        b.strip() for b in re.split(r"(?=KLEE: WARNING)", warnings_text)
        if b.strip()
    ]
    if not blocks:
        return None

    concretizing = 0
    items = []
    for block in blocks:
        lower = block.lower()
        wtype = "other"
        for type_name, keyword in _WARNING_TYPE_KEYWORDS:
            if keyword in lower:
                wtype = type_name
                break
        if wtype == "concretizing":
            concretizing += 1
        items.append({"type": wtype, "message": block})

    return {"total": len(items), "concretizing": concretizing, "items": items}


def extract_error_counts(data: dict) -> dict:
    """从 .err 文件列表中统计错误数量，按类型分组。

    返回：
    {
        "total": <int>,
        "by_type": {"ptr": <int>, "assert": <int>, ...}
    }
    """
    err_files = data.get("err_files", [])
    by_type = {name: 0 for name, _ in _ERR_TYPE_PATTERNS}
    by_type["other"] = 0

    for filename in err_files:
        matched = False
        for type_name, suffix in _ERR_TYPE_PATTERNS:
            if filename.endswith(suffix):
                by_type[type_name] += 1
                matched = True
                break
        if not matched:
            by_type["other"] += 1

    return {"total": len(err_files), "by_type": by_type}


def error_counts(data: dict) -> dict:
    """统计错误数量（含 user 类型）。"""
    return extract_error_counts(data)


def analyze_klee_output(*, klee_output_dir: Path | None, stdout_path: Path | None = None,
                        stderr_path: Path | None = None, timed_out: bool = False) -> dict:
    """分析 KLEE 原始输出，提取关键信息。

    参数：
    - klee_output_dir: KLEE 的 --output-dir 目录
    - stdout_path: KLEE 标准输出文件路径（可选）
    - stderr_path: KLEE 标准错误文件路径（可选）
    - timed_out: 是否超时

    返回：
    {
        "conclusion": "COMPLETED | ERRORS | TIMEOUT | INCOMPLETE",
        "statistics": null | {explored_paths, completed_paths, generated_tests,
                              total_instructions, coverage, termination_reasons, external_calls},
        "warnings": null | {total, concretizing, items},
        "error_summary": null | {total, by_type},
    }
    """
    data = load_klee_output(
        klee_output_dir=klee_output_dir,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )

    conclusion = extract_conclusion(data, timed_out=timed_out)

    statistics = None
    warnings = None
    error_summary = None
    if conclusion != "TIMEOUT":
        statistics = extract_statistics(data)
        warnings = extract_warnings(data)
        counts = extract_error_counts(data)
        if counts["total"] > 0:
            error_summary = counts

    return {
        "conclusion": conclusion,
        "statistics": statistics,
        "warnings": warnings,
        "error_summary": error_summary,
    }
