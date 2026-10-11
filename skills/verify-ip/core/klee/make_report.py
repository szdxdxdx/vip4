"""生成 KLEE 验证报告（report.json + report.html）。

从每个 case 的 result.json 中聚合数据，生成套件级别的 JSON 报告；
同时从 KLEE 原始输出中提取 .err 错误详情，渲染为 HTML 报告。
"""
import json
from copy import deepcopy
from pathlib import Path

import jinja2
from markdown_it import MarkdownIt
from markupsafe import Markup

from core.klee.analyze_klee_output import analyze_klee_output
from core.utils import current_datetime, format_datetime, is_nonfunctional_case, parse_datetime


_ASSETS_DIR = Path(__file__).parent / "assets"
_VALID_OVERALL_RESULTS = {"PASS", "PARTIAL_PASS", "FAIL", "TIMEOUT", "INCONCLUSIVE"}
_VALID_CASE_RESULTS = {"PASS", "FAIL", "TIMEOUT", "PARTIAL_PASS", "INCONCLUSIVE"}
_MARKDOWN_RENDERER = MarkdownIt("commonmark", {"html": False}).enable("table")


def load_json_obj(path: Path) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            value = json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeError):
        return {}
    if not isinstance(value, dict):
        return {}
    return value


def load_markdown(filepath: Path, missing_ok: bool = True) -> Markup | None:
    if not missing_ok and not filepath.is_file():
        raise FileNotFoundError(f"file not found: {filepath}")
    try:
        text = filepath.read_text(encoding="utf-8")
        return Markup(_MARKDOWN_RENDERER.render(text))
    except Exception:
        return None




_KTEST_TOOL = None


def _find_ktest_tool() -> str | None:
    """查找 ktest-tool 可执行文件路径。"""
    global _KTEST_TOOL
    if _KTEST_TOOL is not None:
        return _KTEST_TOOL
    candidates = [
        "/snap/klee/20/usr/local/bin/ktest-tool",
        "/snap/klee/current/usr/local/bin/ktest-tool",
        "/usr/local/bin/ktest-tool",
    ]
    for path in candidates:
        if Path(path).is_file():
            _KTEST_TOOL = path
            return path
    # 搜索 PATH
    import shutil
    path = shutil.which("ktest-tool")
    _KTEST_TOOL = path
    return path


def _parse_ktest(ktest_path: Path) -> list[dict] | None:
    """使用 ktest-tool 解析 .ktest 文件，返回结构化对象列表。

    每项格式：
    {
        "name": <str>,       # 变量名
        "size": <int>,       # 字节大小
        "value_type": "int" | "hex",  # 显示方式
        "value": <str>,      # 显示值
        "c_assignment": <str> # C 赋值语句
    }
    """
    tool = _find_ktest_tool()
    if tool is None or not ktest_path.is_file():
        return None
    import subprocess
    try:
        result = subprocess.run(
            [tool, str(ktest_path)],
            capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    output = result.stdout
    if not output:
        return None

    objects = []
    lines = output.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # 匹配 "object N: name: '<name>'"
        if not line.startswith("object ") or ": name: " not in line:
            i += 1
            continue
        # 解析 name
        name_part = line.split(": name: ", 1)[1].strip().strip("'")
        i += 1

        # 解析 size (下一行: "object N: size: <int>")
        size = 0
        if i < len(lines) and ": size: " in lines[i]:
            size_part = lines[i].split(": size: ", 1)[1].strip()
            size = int(size_part)
            i += 1

        # 跳 data 行
        if i < len(lines) and ": data: " in lines[i]:
            data_line = lines[i]
            i += 1

        # 解析 hex
        hex_value = None
        if i < len(lines) and ": hex : " in lines[i]:
            hex_part = lines[i].split(": hex : ", 1)[1].strip()
            hex_value = hex_part
            i += 1

        # 解析 int (如果有)
        int_value = None
        if i < len(lines) and ": int : " in lines[i]:
            int_part = lines[i].split(": int : ", 1)[1].strip()
            int_value = int(int_part)
            i += 1

        # 构建 C 赋值
        if size == 1 and int_value is not None:
            c_assignment = f"{name_part} = {int_value}"
            value = str(int_value)
            value_type = "int"
        elif size > 1 and hex_value:
            # 将 hex 拆为字节数组
            hex_str = hex_value.removeprefix("0x")
            bytes_list = [str(int(hex_str[j:j+2], 16)) for j in range(0, len(hex_str), 2)]
            array_str = "{" + ", ".join(bytes_list) + "}"
            c_assignment = f"{name_part}[{size}] = {array_str}"
            value = array_str
            value_type = "hex"
        else:
            c_assignment = f"{name_part} = <unreadable>"
            value = "<unreadable>"
            value_type = "unknown"

        objects.append({
            "name": name_part,
            "size": size,
            "value_type": value_type,
            "value": value,
            "c_assignment": c_assignment,
        })

        # 跳剩余行（uint, text 等），直到遇到下一个 "object N:"
        while i < len(lines) and not lines[i].startswith("object "):
            i += 1

    return objects if objects else None


def load_err_contents(suite_dir: Path, case_name: str) -> list[dict] | None:
    """从 KLEE 输出目录中读取 .err 文件内容。

    返回按文件名排序的列表，每项包含 filename、content，
    以及同名的 .ktest 测试输入文件名和解析后的值。
    无 .err 文件或目录不存在时返回 None。
    """
    klee_out = suite_dir / "output" / "klee" / case_name / "klee-out"
    if not klee_out.is_dir():
        return None
    err_files = sorted(klee_out.glob("*.err"))
    if not err_files:
        return None
    contents = []
    for p in err_files:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = "(无法读取错误文件)"
        # 错误文件名格式为 testNNNNNN.<type>.err，对应测试输入为 testNNNNNN.ktest
        ktest_name = f"{p.name[:-len('.err')].split('.', 1)[0]}.ktest"
        ktest_path = klee_out / ktest_name
        ktest_data = _parse_ktest(ktest_path) if ktest_path.is_file() else None
        contents.append({
            "filename": p.name,
            "content": text,
            "ktest_name": ktest_name if ktest_path.is_file() else None,
            "ktest_data": ktest_data,
        })
    return contents if contents else None


def case_result(suite_dir: Path, case_name: str, ai_agent_conclusion: str) -> tuple[dict, dict]:
    """从单个 case 的 result.json 和 KLEE 原始输出中提取报告数据。

    返回 (report_case, detail) 二元组：
    - report_case：用于 JSON 报告的结构
    - detail：用于 HTML 渲染的详细结构（含 .err 内容）
    """
    config = load_json_obj(suite_dir / f"{case_name}.json")
    result = load_json_obj(suite_dir / "output" / "klee" / case_name / "result.json")

    timing = result.get("timing") or {}
    klee_conclusion = result.get("conclusion") or "INCOMPLETE"
    statistics = result.get("statistics")
    error_summary = result.get("error_summary")
    warnings = result.get("warnings")

    splited_from = config.get("splited_from")
    reduced_from = config.get("reduced_from")

    conclusion = {
        "klee": klee_conclusion,
        "ai_agent": ai_agent_conclusion,
    }

    case_timing = {
        "duration": timing.get("duration", 0),
        "timed_out": timing.get("timed_out", False),
    }
    report_case = {
        "splited_from": splited_from,
        "reduced_from": reduced_from,
        "conclusion": conclusion,
        "timing": case_timing,
        "statistics": statistics,
        "warnings": warnings,
        "error_summary": error_summary,
    }

    detail = {
        "name": case_name,
        "conclusion": conclusion,
        "timing": case_timing,
        "statistics": statistics,
        "warnings": warnings,
        "error_summary": error_summary,
        "err_contents": load_err_contents(suite_dir, case_name),
    }

    return report_case, detail


def load_conclusion(path: Path) -> dict:
    """加载 AI Agent 的结论配置。"""
    data = load_json_obj(path)
    overall_data = data.get("overall")
    cases_data = data.get("cases")
    if not isinstance(overall_data, dict):
        overall_data = {}
    if not isinstance(cases_data, dict):
        cases_data = {}

    overall = {}
    for field in ("functional", "nonfunctional"):
        value = overall_data.get(field)
        overall[field] = value if value in _VALID_OVERALL_RESULTS else "INCONCLUSIVE"

    cases = {
        name: value
        for name, value in cases_data.items()
        if isinstance(name, str) and value in _VALID_CASE_RESULTS
    }
    return {"overall": overall, "cases": cases}


def discover_case_names(suite_dir: Path) -> list[str]:
    """发现套件中所有的 case（通过 .json 配置文件）。"""
    names = []
    for path in sorted(suite_dir.glob("case_*.json")):
        if path.with_suffix(".c").is_file():
            names.append(path.stem)
    return names


def build_statistics_aggregate(cases: dict[str, dict]) -> dict:
    """汇总所有 case 的统计信息。"""
    total_explored_paths = 0
    total_generated_tests = 0
    total_errors = 0
    for case_data in cases.values():
        stats = case_data.get("statistics")
        if stats:
            total_explored_paths += stats.get("explored_paths", 0)
            total_generated_tests += stats.get("generated_tests", 0)
        err_summary = case_data.get("error_summary")
        if err_summary:
            total_errors += err_summary.get("total", 0)
    return {
        "total_explored_paths": total_explored_paths,
        "total_generated_tests": total_generated_tests,
        "total_errors": total_errors,
    }


def build_strategy(cases: dict[str, dict]) -> dict:
    """从 case 数据中重建验证策略信息。"""
    originals = []
    reduced = []
    splited: dict[str, list[str]] = {}
    for name, case in cases.items():
        if not case["splited_from"] and not case["reduced_from"]:
            originals.append(name)
        if case["reduced_from"]:
            reduced.append({"original": case["reduced_from"], "reduced": name})
        if case["splited_from"]:
            splited.setdefault(case["splited_from"], []).append(name)
    return {
        "original_cases": originals,
        "reduced_cases": reduced,
        "splited_cases": [
            {"original": original, "splited": names}
            for original, names in splited.items()
        ],
    }


def build_display_cases(suite_dir: Path, details: dict[str, dict]) -> list[dict]:
    """构建用于 HTML 模板渲染的 case 列表。

    按功能性在前、非功能性在后的顺序排列，并加载 AI 分析 Markdown。
    """
    ai_dir = suite_dir / "output" / "ai_agent"
    display_cases = []
    ordered_items = sorted(
        details.items(),
        key=lambda item: (is_nonfunctional_case(item[0]), item[0]),
    )
    for name, detail in ordered_items:
        display_cases.append({
            "name": name,
            "case_type": "nonfunctional" if is_nonfunctional_case(name) else "functional",
            "conclusion": detail["conclusion"],
            "timing": detail["timing"],
            "statistics": detail["statistics"],
            "analysis": load_markdown(ai_dir / f"{name}.md"),
            "detail": detail,
        })
    return display_cases


def make_report(suite_dir: Path):
    """生成 KLEE 验证报告（JSON + HTML）。"""
    suite_dir = suite_dir.resolve()
    suite_dir.mkdir(parents=True, exist_ok=True)
    generated_at = current_datetime()

    suite = load_json_obj(suite_dir / "suite.json")
    ip_name = suite.get("ip", "")

    ai_dir = suite_dir / "output" / "ai_agent"
    conclusion = load_conclusion(ai_dir / "conclusion.json")
    report_cases = {}
    details = {}
    for case_name in discover_case_names(suite_dir):
        ai_agent_conclusion = conclusion["cases"].get(case_name, "INCONCLUSIVE")
        report_case, detail = case_result(suite_dir, case_name, ai_agent_conclusion)
        report_cases[case_name] = report_case
        details[case_name] = detail

    statistics = build_statistics_aggregate(report_cases)

    suite_created = parse_datetime(suite.get("suite_created_at", generated_at))

    report = {
        "ip": ip_name,
        "ai_agent_conclusion": {
            "functional": conclusion["overall"]["functional"],
            "nonfunctional": conclusion["overall"]["nonfunctional"],
        },
        "timing": {
            "suite_created_at": format_datetime(suite_created),
            "report_generated_at": format_datetime(generated_at),
        },
        "strategy": build_strategy(report_cases),
        "cases": report_cases,
        "statistics": statistics,
    }

    output_dir = suite_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 写入 JSON 报告
    json_path = output_dir / "report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"[INFO] 已生成 KLEE 验证报告 {json_path}")

    # 渲染 HTML 报告
    render_report = deepcopy(report)
    render_report["display_cases"] = build_display_cases(suite_dir, details)
    render_report["ai_sections"] = {
        "issues": load_markdown(ai_dir / "issues.md"),
        "conclusion": load_markdown(ai_dir / "conclusion.md", missing_ok=False),
        "experience": load_markdown(ai_dir / "experience.md", missing_ok=False),
    }

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(_ASSETS_DIR)),
        autoescape=jinja2.select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    html_text = env.get_template("report.html").render(report=render_report)
    html_path = output_dir / "report.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_text)
        f.write("\n")
    print(f"[INFO] 已生成 KLEE 验证报告 {html_path}")