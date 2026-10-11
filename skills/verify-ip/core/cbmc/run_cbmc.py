import json
from pathlib import Path
import shlex
import shutil
import subprocess
import time

from core.cbmc.analyze_cbmc_output import assertion_counts, extract_conclusion, extract_properties, load_cbmc_output
from core.utils import elapsed_seconds, check_case_name



def build_cmd(cbmc_config):
    cmd = [cbmc_config.get("executable", "cbmc")]
    for option, val in cbmc_config["options"].items():
        if isinstance(val, bool):
            if val:
                cmd.append(option)
        elif isinstance(val, list):
            for item in val:
                cmd.extend([option, str(item)])
        else:
            cmd.extend([option, str(val)])
    cmd.extend(cbmc_config["files"])
    return cmd


def run_cbmc(*, suite_dir: Path, case: str):
    check_case_name(case)
    suite_dir = suite_dir.resolve()

    config_filepath = suite_dir / f"{case}.json"
    with open(config_filepath, "r", encoding="utf-8") as f:
        config = json.load(f)

    cmd = build_cmd(config["cbmc"])
    timeout = float(config["py_subprocess"]["timeout"])

    output_dir = suite_dir / "output" / "cbmc" / case
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    stdout_path = output_dir / "cbmc_stdout.json"
    stderr_path = output_dir / "cbmc_stderr.txt"
    result_path = output_dir / "result.json"

    timed_out = False
    return_code: None|int = None
    t_start = time.monotonic()
    try:
        with open(stdout_path, "w", encoding="utf-8") as out, open(stderr_path, "w", encoding="utf-8") as err:
            print(
                f"[INFO] subprocess.run(cmd=[{shlex.join(cmd)}], cwd='{shlex.quote(str(suite_dir))}', "
                f"timeout={timeout}, stdout='{shlex.quote(str(stdout_path))}', stderr='{shlex.quote(str(stderr_path))}')"
            )
            try:
                proc = subprocess.run(cmd,  cwd=suite_dir, timeout=timeout, stdout=out, stderr=err, check=False, text=True)
                return_code = proc.returncode
                print(f"[INFO] CBMC 运行结束，退出码 {return_code}")
            except subprocess.TimeoutExpired:
                timed_out = True
    finally:
        duration = elapsed_seconds(t_start, time.monotonic())

        cbmc_out, _ = load_cbmc_output(stdout_path=stdout_path, stderr_path=None)
        if timed_out:
            assertions_count = None
        else:
            properties = extract_properties(cbmc_out)
            assertions_count = assertion_counts(properties)

        result = {
            "conclusion": extract_conclusion(cbmc_out, timed_out=timed_out),
            "return_code": return_code,
            "timing": {
                "duration": duration,
                "timed_out": bool(timed_out),
            },
            "assertions": assertions_count,
        }

        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
            f.write("\n")

    time.sleep(2)
    if timed_out:
        print(f"[ERROR] CBMC 运行超时：{duration} 秒")
        with open(stderr_path, "a", encoding="utf-8") as err:
            err.write("\nCBMC_TIMEOUT\n")
    else:
        print(
            f"[INFO] CBMC 执行用时 {duration} 秒，结论 {result['conclusion']}，"
            f"{assertions_count['total']} 条断言 / "
            f"{assertions_count['passed']} 通过 / "
            f"{assertions_count['failed']} 不通过"
        )
    print(f"[INFO] 结果保存至 {output_dir}")
