import re
from pathlib import Path
from typing import Any

_RESULT_RE = re.compile(r"Verification result:\s*(TRUE|FALSE|UNKNOWN)\b([^\r\n]*)", re.I)
_NUMBER_RE = re.compile(r"^\s*([^:]+):\s*([0-9]+(?:\.[0-9]+)?)\s*(?:s|sec|seconds)?\s*$", re.I)
_ASSERTION_RE = re.compile(
    r'assertion\s+in\s+line\s+(\d+):\s*Condition\s+"(.*?)"\s+failed\s+in\s+"([^"]+)",\s+line\s+(\d+)',
    re.I,
)
_GENERIC_PROPERTY_RE = re.compile(
    r"\((overflow|memory safety|valid-[^)]+)\s+in\s+line\s+(\d+):\s*(.*?)\)",
    re.I,
)
_COUNTEREXAMPLE_EDGE_RE = re.compile(
    r"^(none|line(?:s)?\s+[^:]+):\s+N\d+\s+-\{(.*?)\}->\s+N\d+\s*$"
)
_ASSERT_FAIL_CALL_RE = re.compile(
    r'(?:__)?assert_fail\s*\(\s*"((?:\\.|[^"\\])*)"\s*,\s*"([^"]+)"\s*,\s*(\d+)',
    re.I,
)
_STATISTIC_KEYS = (
    "Bound k",
    "Maximum loop iteration reached",
    "Function coverage",
    "Visited lines",
    "Total lines",
    "Line coverage",
    "Visited conditions",
    "Total conditions",
    "Condition coverage",
    "Number of target states",
    "Time for Analysis",
    "CPU time for analysis",
    "Total time for CPAchecker",
    "Total CPU time for CPAchecker",
)


def read_text(path: Path | None) -> str:
    """读取 UTF-8 文本；文件缺失或不可读时返回空字符串"""
    if path is None:
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def parse_verification_result(stdout: str, stderr: str = "") -> tuple[str | None, str]:
    """提取最后一条 TRUE、FALSE 或 UNKNOWN 结果及其说明"""
    matches = list(_RESULT_RE.finditer(stdout + "\n" + stderr))
    if not matches:
        return None, ""
    match = matches[-1]
    return match.group(1).upper(), match.group(2).strip(" .()")


def parse_statistics(path: Path) -> dict[str, int | float]:
    """从 Statistics.txt 提取适合结果统计的固定核心指标"""
    values: dict[str, int | float] = {}
    for line in read_text(path).splitlines():
        match = _NUMBER_RE.match(line)
        if not match or match.group(1).strip() not in _STATISTIC_KEYS:
            continue
        raw = match.group(2)
        values[match.group(1).strip()] = float(raw) if "." in raw else int(raw)
    return values


def extract_source_assertions(source_path: Path | None) -> list[dict[str, Any]]:
    """从 C 驱动中提取跨行 assert 调用、条件文本和起始行。"""
    text = read_text(source_path)
    assertions = []
    index = 0
    state = "code"
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if state == "line-comment":
            if char == "\n":
                state = "code"
            index += 1
            continue
        if state == "block-comment":
            if char == "*" and next_char == "/":
                state = "code"
                index += 2
            else:
                index += 1
            continue
        if state in ("string", "char"):
            if char == "\\":
                index += 2
            elif (state == "string" and char == '"') or (state == "char" and char == "'"):
                state = "code"
                index += 1
            else:
                index += 1
            continue
        if char == "/" and next_char == "/":
            state = "line-comment"
            index += 2
            continue
        if char == "/" and next_char == "*":
            state = "block-comment"
            index += 2
            continue
        if char == '"':
            state = "string"
            index += 1
            continue
        if char == "'":
            state = "char"
            index += 1
            continue
        match = re.match(r"assert\s*\(", text[index:])
        if not match or (index > 0 and (text[index - 1].isalnum() or text[index - 1] == "_")):
            index += 1
            continue
        line_start = text.rfind("\n", 0, index) + 1
        if text[line_start:index].lstrip().startswith("#"):
            index += len(match.group(0))
            continue

        open_paren = index + match.group(0).rfind("(")
        cursor = open_paren + 1
        depth = 1
        inner_state = "code"
        while cursor < len(text) and depth:
            current = text[cursor]
            following = text[cursor + 1] if cursor + 1 < len(text) else ""
            if inner_state == "line-comment":
                if current == "\n":
                    inner_state = "code"
            elif inner_state == "block-comment":
                if current == "*" and following == "/":
                    inner_state = "code"
                    cursor += 1
            elif inner_state in ("string", "char"):
                if current == "\\":
                    cursor += 1
                elif ((inner_state == "string" and current == '"')
                      or (inner_state == "char" and current == "'")):
                    inner_state = "code"
            elif current == "/" and following == "/":
                inner_state = "line-comment"
                cursor += 1
            elif current == "/" and following == "*":
                inner_state = "block-comment"
                cursor += 1
            elif current == '"':
                inner_state = "string"
            elif current == "'":
                inner_state = "char"
            elif current == "(":
                depth += 1
            elif current == ")":
                depth -= 1
            cursor += 1
        if depth:
            break
        condition = " ".join(text[open_paren + 1:cursor - 1].split())
        assertions.append({
            "id": f"assert_{len(assertions) + 1}",
            "kind": "assertion",
            "file": source_path.name if source_path else None,
            "line": text.count("\n", 0, index) + 1,
            "description": condition,
        })
        index = cursor
    return assertions


def _normalized_condition(value: str) -> str:
    """规范化条件中的空白和冗余外层括号，供失败断言匹配。"""
    normalized = "".join(value.split())
    while normalized.startswith("(") and normalized.endswith(")"):
        depth = 0
        wraps_all = True
        for index, char in enumerate(normalized):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0 and index != len(normalized) - 1:
                    wraps_all = False
                    break
        if not wraps_all:
            break
        normalized = normalized[1:-1]
    return normalized


def parse_confirmed_violations(stdout: str, raw_result: str | None,
                               source_path: Path | None = None) -> tuple[list[dict[str, Any]], int]:
    """提取 CPAchecker 明确报告的违规点，不推断其他断言的逐条状态。"""
    source_assertions = extract_source_assertions(source_path)
    if raw_result != "FALSE":
        return [], len(source_assertions)

    violations = []
    for match in _ASSERTION_RE.finditer(stdout):
        reported_file = Path(match.group(3)).name
        reported_line = int(match.group(4))
        expression = match.group(2).strip()
        source_match = next((
            assertion for assertion in source_assertions
            if assertion["file"] == reported_file and assertion["line"] == reported_line
        ), None)
        if source_match is None:
            expression_matches = [
                assertion for assertion in source_assertions
                if _normalized_condition(assertion["description"])
                == _normalized_condition(expression)
            ]
            source_match = expression_matches[0] if len(expression_matches) == 1 else None
        violations.append({
            "id": source_match["id"] if source_match else f"violation_{len(violations) + 1}",
            "kind": "assertion",
            "file": source_match["file"] if source_match else reported_file,
            "line": source_match["line"] if source_match else reported_line,
            "expression": source_match["description"] if source_match else expression,
        })
    for match in _GENERIC_PROPERTY_RE.finditer(stdout):
        violations.append({
            "id": f"violation_{len(violations) + 1}",
            "kind": match.group(1).lower(),
            "file": None,
            "line": int(match.group(2)),
            "expression": match.group(3).strip(),
        })
    unique = []
    seen = set()
    for violation in violations:
        key = (violation["kind"], violation["file"], violation["line"], violation["expression"])
        if key not in seen:
            seen.add(key)
            unique.append(violation)
    return unique, len(source_assertions)


def parse_counterexample(path: Path) -> dict[str, Any]:
    """从文本反例中筛选关键路径，并识别对应断言目标。"""
    steps = []
    current = None
    for line in read_text(path).splitlines():
        match = _COUNTEREXAMPLE_EDGE_RE.match(line)
        if match:
            operation = match.group(2).strip()
            current = None
            if (not operation or operation == "INIT GLOBAL VARS" or operation == "0;"
                    or operation.startswith(("typedef ", "struct "))
                    or "dummy edge" in operation.lower()):
                continue
            current = {
                "location": "" if match.group(1) == "none" else match.group(1),
                "operation": operation,
                "values": [],
            }
            steps.append(current)
            continue
        value = line.strip().rstrip(";")
        if current is not None and value and "==" in value and value not in current["values"]:
            if len(current["values"]) < 3:
                current["values"].append(value)
    # selected = steps[-max_steps:]
    selected = steps
    target = None
    for step in reversed(selected):
        match = _ASSERT_FAIL_CALL_RE.search(step["operation"])
        if match:
            target = {
                "file": Path(match.group(2)).name,
                "line": int(match.group(3)),
                "expression": bytes(match.group(1), "utf-8").decode("unicode_escape"),
            }
            break
    return {
        "target": target,
        "steps": selected,
        # "truncated": len(steps) > max_steps
    }


def parse_counterexamples(output_dir: Path, violations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """解析标准文本反例，并将每条路径关联到明确违规点。"""
    if not output_dir.is_dir():
        return []
    paths = sorted(
        path for path in output_dir.glob("Counterexample.*.txt")
        if not path.name.endswith((".assignment.txt", ".core.txt"))
    )
    parsed = []
    used = set()
    for path in paths:
        trace = parse_counterexample(path)
        target = trace.pop("target")
        violation = None
        if target:
            violation = next((item for item in violations if (
                item["file"] == target["file"] and item["line"] == target["line"]
            )), None)
            if violation is None:
                matches = [item for item in violations if (
                    _normalized_condition(item["expression"])
                    == _normalized_condition(target["expression"])
                )]
                violation = matches[0] if len(matches) == 1 else None
        if violation is None:
            violation = next((item for item in violations if item["id"] not in used), None)
        if violation:
            used.add(violation["id"])
        parsed.append({"violation_id": violation["id"] if violation else None, **trace})
    return parsed


def _error_message(stdout: str, stderr: str) -> str:
    """从无最终结果的工具输出中选择最有用的一行错误摘要"""
    lines = [line.strip() for line in (stdout + "\n" + stderr).splitlines() if line.strip()]
    markers = ("fatal error:", "error:", "severe", "parsing failed", "conversion error", "exception")
    for line in reversed(lines):
        if any(marker in line.lower() for marker in markers):
            return line
    return lines[-1] if lines else ""


def _warning_summary(lines: list[str]) -> list[dict[str, Any]]:
    """将重复的 soundness logger 行按风险类型和函数归并。"""
    groups: dict[tuple[str, str | None], int] = {}
    for line in lines:
        lower = line.lower()
        if "unknown and unhandled function call" in lower:
            category = "UNKNOWN_FUNCTION"
            match = re.search(r"unknown and unhandled function call\s+([A-Za-z_]\w*)", line, re.I)
            subject = match.group(1) if match else None
        elif "overapproxim" in lower:
            category, subject = "OVERAPPROXIMATION", None
        elif "side-effects" in lower and "ignored" in lower:
            category, subject = "IGNORED_SIDE_EFFECTS", None
        else:
            category, subject = "OTHER_SOUNDNESS_RISK", None
        groups[(category, subject)] = groups.get((category, subject), 0) + 1
    return [
        {"category": category, "subject": subject, "count": count}
        for (category, subject), count in groups.items()
    ]


def _goal_kind(config: dict | None) -> str:
    """根据 case 配置概括 specification 目标类别。"""
    options = (config or {}).get("cpachecker", {}).get("options", {})
    specification = " ".join(str(value) for value in (
        options.get("-spec", ""), options.get("-config", "")
    )).lower()
    if "overflow" in specification:
        return "integer-overflow"
    if any(word in specification for word in ("memory", "valid-", "reachsafety")):
        return "memory-safety"
    if "assert" in specification:
        return "assertion-reachability"
    return "specification-reachability"


def _interpretation(raw_result: str | None, timed_out: bool, tool_error: bool) -> str:
    """把 CPAchecker 原始结果映射为稳定、无日志正文的解释代码。"""
    if timed_out:
        return "TIME_LIMIT_REACHED"
    if tool_error:
        return "TOOL_ERROR"
    return {
        "TRUE": "NO_REACHABLE_VIOLATION",
        "FALSE": "REACHABLE_VIOLATION",
        "UNKNOWN": "NO_FINAL_CONCLUSION",
    }.get(raw_result, "NO_FINAL_CONCLUSION")


def analyze_output(*, stdout_path: Path, stderr_path: Path, output_dir: Path,
                   return_code: int | None, timed_out: bool, duration: float,
                   source_path: Path | None = None, config: dict | None = None) -> dict[str, Any]:
    """把一次 CPAchecker 执行归纳为紧凑、可统计的 case 结果"""
    stdout, stderr = read_text(stdout_path), read_text(stderr_path)
    raw_result, message = parse_verification_result(stdout, stderr)
    combined = stdout + "\n" + stderr
    error_markers = (
        "Exception in thread", "CPAchecker terminated with an error", "Parsing failed",
        "CONVERSION ERROR", "Could not parse", "java.lang.", "VerifyException",
    )
    specification_warnings = list(dict.fromkeys(
        line.strip() for line in combined.splitlines()
        if "specification" in line.lower()
        and any(word in line.lower() for word in ("ignore", "not match", "not monitored"))
    ))
    warning_lines = list(dict.fromkeys(
        line.strip() for line in combined.splitlines()
        if "warning" in line.lower()
        and any(word in line.lower() for word in (
            "sound", "overapproxim", "unknown and unhandled function", "side-effects",
        ))
    ))
    tool_error = not timed_out and raw_result is None and (
        return_code not in (None, 0) or any(marker.lower() in combined.lower() for marker in error_markers)
    )
    conclusion = "TIMEOUT" if timed_out else raw_result

    if raw_result is None and tool_error:
        message = _error_message(stdout, stderr)

    violations, source_count = parse_confirmed_violations(combined, raw_result, source_path)
    counterexamples = parse_counterexamples(output_dir, violations) if raw_result == "FALSE" else []
    return {
        "return_code": return_code,
        "timing": {"duration": duration, "timed_out": timed_out},
        "conclusion": conclusion,
        "verification_goal": {
            "kind": _goal_kind(config),
            "interpretation": _interpretation(raw_result, timed_out, tool_error),
        },
        "tool_error": tool_error,
        "error_summary": message if raw_result is None and tool_error else "",
        "assertions": {
            "source_count": source_count,
            "monitoring": "MISMATCH_REPORTED" if specification_warnings else "NO_MISMATCH_REPORTED",
            "confirmed_violation_count": len(violations),
            "confirmed_violations": violations,
        },
        "statistics": parse_statistics(output_dir / "Statistics.txt"),
        "counterexamples": {
            "available": len(counterexamples),
            "mapped": sum(item.get("violation_id") is not None for item in counterexamples),
        },
        "warnings": {
            "specification": {"count": len(specification_warnings)},
            "soundness": _warning_summary(warning_lines),
        },
    }
