import json
from copy import deepcopy
from pathlib import Path

import jinja2
from markdown_it import MarkdownIt
from markupsafe import Markup

from core.cpachecker.analyze_cpachecker_output import parse_counterexamples
from core.utils import current_datetime, format_datetime, parse_datetime

_ASSETS_DIR = Path(__file__).parent / "assets"
_VALID_OVERALL = {"PASS", "PARTIAL_PASS", "FAIL", "TIMEOUT", "INCONCLUSIVE"}
_VALID_CASE = {"PASS", "PARTIAL_PASS", "FAIL", "TIMEOUT", "INCONCLUSIVE"}
_MARKDOWN_RENDERER = MarkdownIt("commonmark", {"html": False}).enable("table")


def load_json(path: Path) -> dict:
    """读取 JSON 对象；文件无效时返回空字典。"""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}


def load_markdown(path: Path, missing_ok: bool = True) -> Markup | None:
    if not missing_ok and not path.is_file():
        raise FileNotFoundError(f"file not found: {path}")
    try:
        return Markup(_MARKDOWN_RENDERER.render(path.read_text(encoding="utf-8")))
    except OSError:
        return None


def discover_configs(suite_dir: Path) -> list[Path]:
    """发现同时具有 C 驱动的 case 配置。"""
    return [
        path for path in sorted(suite_dir.glob("case_*.json"))
        if path.with_suffix(".c").is_file()
    ]


def load_conclusion(path: Path) -> dict:
    """读取并校验 AI Agent 给出的结论。"""
    value = load_json(path)
    overall = value.get("overall") if isinstance(value.get("overall"), dict) else {}
    cases = value.get("cases") if isinstance(value.get("cases"), dict) else {}
    return {
        "overall": {
            key: overall.get(key) if overall.get(key) in _VALID_OVERALL else "INCONCLUSIVE"
            for key in ("functional", "nonfunctional")
        },
        "cases": {
            key: val for key, val in cases.items()
            if isinstance(key, str) and val in _VALID_CASE
        },
    }


def _case_type(case: dict) -> str:
    """根据 verification goal 区分功能性与非功能性，未知目标安全回退为功能性。"""
    return (
        "nonfunctional"
        if case["verification"]["kind"] in ("memory-safety", "integer-overflow")
        else "functional"
    )


def build_strategy(cases: dict) -> dict:
    """整理原 case、拆分 case 和缩减 case 的直接派生关系。"""
    originals, reduced, split = [], [], {}
    for name, item in cases.items():
        if not item["splited_from"] and not item["reduced_from"]:
            originals.append(name)
        if item["reduced_from"]:
            reduced.append({"original": item["reduced_from"], "reduced": name})
        if item["splited_from"]:
            split.setdefault(item["splited_from"], []).append(name)
    return {
        "original_cases": originals,
        "reduced_cases": reduced,
        "splited_cases": [
            {"original": parent, "splited": children}
            for parent, children in split.items()
        ],
    }


def _list(value) -> list:
    """把非列表值安全地转换为空列表。"""
    return value if isinstance(value, list) else []


def _tool_result(result: dict) -> str | None:
    """读取字段说明允许的 CPAchecker 原始结果。"""
    value = result.get("conclusion")
    return value if value in ("TRUE", "FALSE", "UNKNOWN") else None


def _interpretation(result: dict) -> str:
    """生成稳定的 CPAchecker 结果解释代码。"""
    if result.get("timing", {}).get("timed_out"):
        return "TIME_LIMIT_REACHED"
    if result.get("tool_error"):
        return "TOOL_ERROR"
    return {
        "TRUE": "NO_REACHABLE_VIOLATION",
        "FALSE": "REACHABLE_VIOLATION",
        "UNKNOWN": "NO_FINAL_CONCLUSION",
    }.get(_tool_result(result), "NO_FINAL_CONCLUSION")


def _result_details(result: dict, output_dir: Path | None = None) -> dict:
    """读取 CPAChecker 结果字段。"""
    assertions = result.get("assertions")
    goal = result.get("verification_goal")
    warnings = result.get("warnings")
    if not isinstance(assertions, dict) or not isinstance(goal, dict) or not isinstance(warnings, dict):
        raise ValueError("CPAchecker result.json 缺少字段说明要求的字段")
    specification = warnings.get("specification")
    if not isinstance(specification, dict):
        raise ValueError("CPAchecker result.json 缺少 warnings.specification")
    violations = [item for item in _list(assertions.get("confirmed_violations")) if isinstance(item, dict)]
    counterexamples = (
        parse_counterexamples(output_dir, violations)
        if output_dir and _tool_result(result) == "FALSE" else []
    )
    return {
        "goal": {
            "kind": goal.get("kind", "specification-reachability"),
            "interpretation": goal.get("interpretation", _interpretation(result)),
        },
        "source_count": int(assertions.get("source_count", 0)),
        "monitoring": assertions.get("monitoring", "UNKNOWN"),
        "violations": violations,
        "counterexamples": counterexamples,
        "specification_warning_count": int(specification.get("count", 0)),
        "soundness": [item for item in _list(warnings.get("soundness")) if isinstance(item, dict)],
    }


def _warning_evidence(output_dir: Path, specification_count: int, soundness: list[dict]) -> dict:
    """从 CPAchecker case 产物提取与结果可信度直接相关的原始警告。"""
    lines = []
    for filename in ("cpachecker_stderr.txt", "cpachecker_stdout.txt"):
        path = output_dir.parent / filename
        try:
            lines.extend(path.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            pass
    specification = []
    soundness_lines = []
    for line in lines:
        text = line.strip()
        lower = text.lower()
        if specification_count and (
            "ignored by this specification" in lower
            or "cannot map specification" in lower
            or "specification" in lower and ("warning" in lower or "ignore" in lower)
        ):
            if text not in specification:
                specification.append(text)
        if soundness and (
            "overapproximated" in lower
            or "side-effects" in lower
            or "side effects" in lower
            or "analysis may no longer be sound" in lower
            or "unknown and unhandled function" in lower
        ):
            if text not in soundness_lines:
                soundness_lines.append(text)
    return {"specification": specification, "soundness": soundness_lines}


def _configured_goal(config: dict) -> str:
    """根据 case 配置概括 verification goal，不依赖项目专有名称。"""
    options = config.get("cpachecker", {}).get("options", {})
    text = " ".join(str(options.get(key, "")) for key in ("-spec", "-config")).lower()
    if "overflow" in text:
        return "integer-overflow"
    if any(word in text for word in ("memory", "valid-", "reachsafety")):
        return "memory-safety"
    if "assert" in text:
        return "assertion-reachability"
    return "specification-reachability"


def _scope(config: dict, details: dict, statistics: dict) -> dict:
    """提取少量直接影响验证范围解释的配置。"""
    options = config.get("cpachecker", {}).get("options", {})
    set_properties = options.get("-setprop") if isinstance(options.get("-setprop"), dict) else {}
    return {
        "configuration": options.get("-config"),
        "specification": options.get("-spec"),
        "entry_function": options.get("-entryfunction"),
        "source_assertions": details["source_count"],
        "loop_bound": set_properties.get("cpa.loopbound.maxLoopIterations"),
        "maximum_loop_iteration_reached": statistics.get("Maximum loop iteration reached"),
    }


def case_data(suite_dir: Path, config_path: Path, ai_conclusion: str) -> tuple[dict, dict]:
    """构建最终 JSON 摘要与 HTML 专用详细数据。"""
    name = config_path.stem
    config = load_json(config_path)
    result_dir = suite_dir / "output" / "cpachecker" / name
    result = load_json(result_dir / "result.json")
    details = _result_details(result, result_dir / "cpachecker_output")
    if details["goal"]["kind"] == "specification-reachability":
        details["goal"]["kind"] = _configured_goal(config)
    statistics = result.get("statistics") if isinstance(result.get("statistics"), dict) else {}
    traces_by_violation = {}
    for trace in details["counterexamples"]:
        traces_by_violation.setdefault(trace.get("violation_id"), []).append(trace)
    available = sum(bool(traces_by_violation.get(item.get("id"))) for item in details["violations"])
    soundness_count = sum(int(item.get("count", 0)) for item in details["soundness"])
    if details["specification_warning_count"]:
        trust_status = "INVALID"
    elif soundness_count:
        trust_status = "REVIEW"
    else:
        trust_status = "CLEAR"
    timed_out = bool(result.get("timing", {}).get("timed_out"))
    raw_result = _tool_result(result)
    tool_conclusion = "TIMEOUT" if timed_out else raw_result
    warning_evidence = _warning_evidence(
        result_dir / "cpachecker_output",
        details["specification_warning_count"],
        details["soundness"],
    )
    summary = {
        "splited_from": config.get("splited_from"),
        "reduced_from": config.get("reduced_from"),
        "conclusion": {
            "cpachecker": tool_conclusion,
            "ai_agent": ai_conclusion,
        },
        "verification": {
            "result": raw_result,
            **details["goal"],
        },
        "scope": _scope(config, details, statistics),
        "violations": {
            "confirmed": len(details["violations"]),
            "extracted_trace_count": len(details["counterexamples"]),
            "counterexamples_available": available,
            "counterexamples_missing": max(0, len(details["violations"]) - available),
        },
        "trust": {
            "status": trust_status,
            "specification_warning_count": details["specification_warning_count"],
            "soundness_warning_count": soundness_count,
            "soundness_categories": len(details["soundness"]),
        },
        "execution": {
            "duration": result.get("timing", {}).get("duration", 0),
            "timed_out": timed_out,
            "tool_error": bool(result.get("tool_error")),
        },
        "error_summary": result.get("error_summary", "") if result.get("tool_error") else "",
    }
    html = deepcopy(summary)
    html.update({
        "confirmed_violations": details["violations"],
        "traces_by_violation": traces_by_violation,
        "soundness": details["soundness"],
        "warning_evidence": warning_evidence,
    })
    return summary, html


def _case_statistics(cases: dict, names: list[str]) -> dict:
    """汇总一组 case 的 CPAchecker 原始结果分布。"""
    selected = [cases[name] for name in names]
    counts = {key: 0 for key in ("true", "false", "unknown", "timeout", "tool_error")}
    for case in selected:
        result = case["verification"]["result"]
        if result in ("TRUE", "FALSE", "UNKNOWN"):
            counts[result.lower()] += 1
        if case["execution"]["timed_out"]:
            counts["timeout"] += 1
        if case["execution"]["tool_error"]:
            counts["tool_error"] += 1
    conclusive = counts["true"] + counts["false"]
    return {
        "total": len(selected),
        **counts,
        "conclusive": conclusive,
        "conclusive_rate": round(conclusive / len(selected), 4) if selected else 0,
        "original": sum(not case["splited_from"] and not case["reduced_from"] for case in selected),
        "sub_cases": sum(bool(case["splited_from"]) for case in selected),
        "reduced_cases": sum(bool(case["reduced_from"]) for case in selected),
    }


def build_statistics(cases: dict) -> dict:
    """生成适合实验统计的 case、违规、可信度和执行宏观指标。"""
    names = list(cases)
    functional = [name for name in names if _case_type(cases[name]) == "functional"]
    nonfunctional = [name for name in names if _case_type(cases[name]) == "nonfunctional"]
    all_cases = _case_statistics(cases, names)
    durations = [float(case["execution"]["duration"] or 0) for case in cases.values()]
    return {
        "cases": all_cases,
        "functional": _case_statistics(cases, functional),
        "nonfunctional": _case_statistics(cases, nonfunctional),
        "violations": {
            "violating_cases": sum(case["violations"]["confirmed"] > 0 for case in cases.values()),
            "confirmed_occurrences": sum(case["violations"]["confirmed"] for case in cases.values()),
            "missing_counterexamples": sum(case["violations"]["counterexamples_missing"] for case in cases.values()),
        },
        "trust": {
            "specification_warning_cases": sum(case["trust"]["specification_warning_count"] > 0 for case in cases.values()),
            "soundness_warning_cases": sum(case["trust"]["soundness_warning_count"] > 0 for case in cases.values()),
            "tool_error_cases": sum(case["execution"]["tool_error"] for case in cases.values()),
        },
        "execution": {
            "total_duration": round(sum(durations), 3),
            "maximum_case_duration": max(durations, default=0),
        },
    }


def make_report(suite_dir: Path):
    """生成宏观 JSON 报告和适合人工审阅的 CPAchecker HTML 报告。"""
    suite_dir = suite_dir.resolve()
    suite = load_json(suite_dir / "suite.json")
    ai_dir = suite_dir / "output" / "ai_agent"
    ai = load_conclusion(ai_dir / "conclusion.json")
    cases, html_cases = {}, {}
    for config_path in discover_configs(suite_dir):
        name = config_path.stem
        cases[name], html_cases[name] = case_data(
            suite_dir, config_path, ai["cases"].get(name, "INCONCLUSIVE")
        )

    created = parse_datetime(suite["suite_created_at"])
    generated = current_datetime()
    report = {
        "ip": suite["ip"],
        "ai_agent_conclusion": {
            "functional": ai["overall"]["functional"],
            "nonfunctional": ai["overall"]["nonfunctional"],
        },
        "timing": {
            "suite_created_at": format_datetime(created),
            "report_generated_at": format_datetime(generated),
        },
        "strategy": build_strategy(cases),
        "cases": cases,
        "statistics": build_statistics(cases),
    }

    output = suite_dir / "output"
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[INFO] 已生成 CPAchecker 验证报告 {json_path}")

    render = deepcopy(report)
    render["display_cases"] = [
        {
            "name": name,
            "case_type": _case_type(cases[name]),
            **html_cases[name],
            "analysis": load_markdown(ai_dir / f"{name}.md"),
        }
        for name in sorted(cases, key=lambda item: (_case_type(cases[item]) == "nonfunctional", item))
    ]
    render["ai_sections"] = {
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
    html_path = output / "report.html"
    html_path.write_text(env.get_template("report.html").render(report=render) + "\n", encoding="utf-8")
    print(f"[INFO] 已生成 CPAchecker 验证报告 {html_path}")
