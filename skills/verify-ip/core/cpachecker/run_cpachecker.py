import json
from pathlib import Path
import os
import shlex
import signal
import shutil
import subprocess
import time

from core.cpachecker.analyze_cpachecker_output import analyze_output
from core.utils import check_case_name, elapsed_seconds

def _items(value):
    """把单值、列表或空值统一转换为列表。"""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def build_cmd(*, suite_dir: Path, config: dict, output_dir: Path) -> list[str]:
    """根据 case 配置构建 CPAchecker 命令，路径相对套件目录解析。"""
    cpa = config["cpachecker"]
    options = cpa.get("options", {})

    def resolve_path(value):
        return str((suite_dir / str(value)).resolve())

    files = [resolve_path(value) for value in _items(cpa.get("files"))]
    includes = [resolve_path(value) for value in _items(options.get("-I"))]
    cmd = [cpa.get("executable", "cpachecker")]

    definitions = [f"-D{value}" for value in _items(options.get("-D"))]
    include_flags = [f"-I{value}" for value in includes]
    if definitions or include_flags:
        preprocessor = "cpp -P " + " ".join(shlex.quote(v) for v in definitions + include_flags)
        cmd.extend(["--preprocess", "--option", f"parser.preprocessor={preprocessor}"])

    aliases = {
        "-config": "--config", "-spec": "--spec",
        "-entryfunction": "--entry-function", "-setprop": "--option",
    }

    def option_value(key, value):
        """规范化布尔 property 及配置文件路径。"""
        if isinstance(value, bool):
            return str(value).lower()
        if key in ("-config", "--config", "-spec", "--spec"):
            return resolve_path(value)
        return str(value)

    for key, value in options.items():
        if key in ("-I", "-D") or value is False or value is None:
            continue
        option = aliases.get(key, key)
        if key in ("-setprop", "--option") and isinstance(value, dict):
            for prop, prop_value in value.items():
                cmd.extend([option, f"{prop}={option_value(key, prop_value)}"])
        elif isinstance(value, bool):
            cmd.append(option)
        else:
            for item in _items(value):
                cmd.extend([option, option_value(key, item)])

    return cmd + ["--output-path", str(output_dir.resolve())] + files


def run_cpachecker(*, suite_dir: Path, case: str):
    """覆盖执行一个 case，并保存 stdout、stderr、工具产物和简要结果。"""
    check_case_name(case)
    suite_dir = suite_dir.resolve()
    with open(suite_dir / f"{case}.json", encoding="utf-8") as f:
        config = json.load(f)
    if not config.get("cpachecker", {}).get("files"):
        raise ValueError("配置缺少 cpachecker.files")

    case_dir = suite_dir / "output" / "cpachecker" / case
    if case_dir.exists():
        shutil.rmtree(case_dir)
    tool_dir = case_dir / "cpachecker_output"
    tool_dir.mkdir(parents=True)
    stdout_path = case_dir / "cpachecker_stdout.txt"
    stderr_path = case_dir / "cpachecker_stderr.txt"
    result_path = case_dir / "result.json"
    cmd = build_cmd(
        suite_dir=suite_dir,
        config=config,
        output_dir=tool_dir,
    )
    timeout = float(config.get("py_subprocess", {}).get("timeout", 600))

    timed_out = False
    launch_error = False
    return_code = None
    start = time.monotonic()
    try:
        print(
            f"[INFO] subprocess.Popen(cmd=[{shlex.join(cmd)}], cwd='{shlex.quote(str(suite_dir))}', "
            f"timeout={timeout}, stdout='{shlex.quote(str(stdout_path))}', stderr='{shlex.quote(str(stderr_path))}')"
        )
        with open(stdout_path, "w", encoding="utf-8") as out, open(stderr_path, "w", encoding="utf-8") as err:
            try:
                with subprocess.Popen(cmd, cwd=suite_dir, stdout=out, stderr=err,
                                      text=True, start_new_session=True) as proc:
                    try:
                        return_code = proc.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        timed_out = True
                        # 同时终止启动脚本和 Java 子进程，避免超时后继续验证。
                        try:
                            os.killpg(proc.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        proc.wait()
            except OSError as exc:
                launch_error = True
                err.write(f"无法启动 CPAchecker：{exc}\n")
    finally:
        duration = elapsed_seconds(start, time.monotonic())
        result = analyze_output(
            stdout_path=stdout_path, stderr_path=stderr_path, output_dir=tool_dir,
            return_code=return_code, timed_out=timed_out, duration=duration,
            source_path=suite_dir / f"{case}.c", config=config,
        )
        if launch_error:
            result["tool_error"] = True
        result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[INFO] CPAchecker 执行用时 {duration} 秒，结论 {result['conclusion']}")
    print(f"[INFO] 结果保存至 {case_dir}")
