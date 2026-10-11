import json
from pathlib import Path
from typing import Any


def load_cbmc_output(stdout_path: Path | None, stderr_path: Path | None) -> tuple[list[Any], str]:
    cbmc_out: list[Any] = []
    cbmc_err = ""
    if stdout_path is not None:
        try:
            value = json.loads(stdout_path.read_text(encoding="utf-8"))
            if isinstance(value, list):
                cbmc_out = value
        except (OSError, json.JSONDecodeError, UnicodeError):
            pass
    if stderr_path is not None:
        try:
            cbmc_err = stderr_path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeError):
            pass
    return cbmc_out, cbmc_err


def extract_conclusion(cbmc_out: list[Any], *, timed_out: bool) -> str:
    if timed_out:
        return "TIMEOUT"
    for item in reversed(cbmc_out):
        if not isinstance(item, dict):
            continue
        status = str(item.get("cProverStatus", "")).upper()
        if status:
            return status
    return ""


def extract_trace(trace_items: Any) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if not isinstance(trace_items, list):
        return steps
    for step in trace_items:
        if not isinstance(step, dict) or step.get("hidden"):
            continue
        src = step.get("sourceLocation") or {}
        if not isinstance(src, dict):
            src = {}
        file = src.get("file", "")
        file = file if isinstance(file, str) else str(file)
        if file.startswith("<"):
            continue

        step_type = step.get("stepType")
        if step_type == "assignment":
            lhs = step.get("lhs", "")
            lhs = lhs if isinstance(lhs, str) else str(lhs)
            if any(lhs.startswith(prefix) for prefix in ("__CPROVER", "return_value_")):
                continue
            value = step.get("value") or {}
            if not isinstance(value, dict):
                value = {}
            data = value.get("data") or ""
            data = data if isinstance(data, str) else str(data)
            if not data or "!" in data:
                continue
            steps.append({
                "kind": "assignment",
                "file": Path(file).name,
                "line": src.get("line", ""),
                "function": src.get("function", ""),
                "lhs": lhs,
                "value": data,
                "type": value.get("type") or "",
            })
        elif step_type in ("function-call", "function-return"):
            function = step.get("function") or {}
            if not isinstance(function, dict):
                function = {}
            name = function.get("displayName") or function.get("identifier", "")
            name = name if isinstance(name, str) else str(name)
            if not name.startswith("__CPROVER"):
                steps.append({
                    "kind": "call" if step_type == "function-call" else "return",
                    "file": Path(file).name,
                    "line": src.get("line", ""),
                    "function": name,
                })
        elif step_type == "failure":
            steps.append({
                "kind": "failure",
                "file": Path(file).name,
                "line": src.get("line", ""),
                "function": src.get("function", ""),
                "reason": step.get("reason", ""),
            })
    return steps


def extract_properties(cbmc_out: list[Any]) -> list[dict[str, Any]]:
    properties: list[dict[str, Any]] = []
    for item in cbmc_out:
        if not isinstance(item, dict) or not isinstance(item.get("result"), list):
            continue
        for result in item["result"]:
            if not isinstance(result, dict):
                continue
            status = str(result.get("status", "UNKNOWN")).upper()
            properties.append({
                "status": status,
                "property": result.get("property", ""),
                "description": result.get("description", ""),
                "trace": extract_trace(result.get("trace")) if status == "FAILURE" else [],
            })
    return properties


def assertion_counts(properties: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "total": len(properties),
        "passed": sum(item.get("status") == "SUCCESS" for item in properties),
        "failed": sum(item.get("status") == "FAILURE" for item in properties),
    }
