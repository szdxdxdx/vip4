import json
from copy import deepcopy
from pathlib import Path

import jinja2
from markdown_it import MarkdownIt
from markupsafe import Markup

from core.cbmc.analyze_cbmc_output import load_cbmc_output, extract_properties
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


def load_conclusion(path: Path) -> dict:
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


def normalize_cbmc_conclusion(value: str | None) -> str:
    status = str(value or "").upper()
    return {"PASS": "SUCCESS", "FAIL": "FAILURE"}.get(status, status)


def case_result(suite_dir: Path, config_path: Path, ai_agent_conclusion: str) -> tuple[dict, dict]:
    case_name = config_path.stem
    config = load_json_obj(config_path)
    output_dir = suite_dir / "output" / "cbmc" / case_name
    with open(output_dir / "result.json", encoding="utf-8") as f:
        result = json.load(f)
    timing = result["timing"]
    cbmc_out, _ = load_cbmc_output(stdout_path=output_dir / "cbmc_stdout.json", stderr_path=None)
    results = extract_properties(cbmc_out)
    counts = result["assertions"]
    splited_from = config["splited_from"]
    reduced_from = config["reduced_from"]
    cbmc_conclusion = normalize_cbmc_conclusion(result.get("conclusion"))
    conclusion = {
        "cbmc": cbmc_conclusion,
        "ai_agent": ai_agent_conclusion,
    }

    report_case = {
        "conclusion": conclusion,
        "splited_from": splited_from,
        "reduced_from": reduced_from,
        "timing": timing,
        "assertions": counts,
    }
    detail = {
        "name": case_name,
        "conclusion": conclusion,
        "timing": timing,
        "statistics": counts,
        "results": results,
    }
    return report_case, detail


def discover_configs(suite_dir: Path) -> list[Path]:
    return [
        config for config in sorted(suite_dir.glob("case_*.json"))
        if config.with_suffix(".c").is_file()
    ]


def build_strategy(cases: dict[str, dict]) -> dict:
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
    ai_dir = suite_dir / "output" / "ai_agent"
    display_cases = []
    # 按功能性在前、非功能性在后
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
    suite_dir = suite_dir.resolve()
    suite_dir.mkdir(parents=True, exist_ok=True)
    generated_at = current_datetime()

    suite = load_json_obj(suite_dir / "suite.json")
    ip_name = suite["ip"]

    ai_dir = suite_dir / "output" / "ai_agent"
    conclusion = load_conclusion(ai_dir / "conclusion.json")
    report_cases = {}
    details = {}
    for path in discover_configs(suite_dir):
        ai_agent_conclusion = conclusion["cases"].get(path.stem, "INCONCLUSIVE")
        report_case, detail = case_result(suite_dir, path, ai_agent_conclusion)
        report_cases[path.stem] = report_case
        details[path.stem] = detail

    assertions = {
        key: sum(
            case["assertions"][key] for case in report_cases.values()
            if case["assertions"] is not None
        )
        for key in ("total", "passed", "failed")
    }

    suite_created = parse_datetime(suite["suite_created_at"])

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
        "assertions": assertions,
    }

    output_dir = suite_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"[INFO] 已生成 CBMC 验证报告 {json_path}")

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
    print(f"[INFO] 已生成 CBMC 验证报告 {html_path}")
