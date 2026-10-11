import json
from pathlib import Path
import shlex
import shutil
import subprocess
import time

from core.klee.analyze_klee_output import analyze_klee_output
from core.utils import check_case_name, elapsed_seconds


def _build_klee_cmd(klee_config: dict) -> list[str]:
    """构建 KLEE 命令，将 bc_file 放在最后。
    
    KLEE 命令格式：klee [options] bc_file [program-args]
    其中 --entry-point 由 entry_point 字段生成并加入 options。
    """
    executable = klee_config.get("executable", "klee")
    cmd = [executable]

    options = klee_config.get("options", {})

    # 处理 --entry-point：从 entry_point 字段生成，避免与 options 中的重复
    entry_point = klee_config.get("entry_point")
    if entry_point:
        cmd.extend(["--entry-point", entry_point])

    # 处理其他 options
    for option, val in options.items():
        if option == "--entry-point":
            continue  # 已在上面处理
        if isinstance(val, bool):
            if val:
                cmd.append(option)
        elif isinstance(val, list):
            for item in val:
                cmd.extend([option, str(item)])
        else:
            cmd.extend([option, str(val)])

    # bc_file 放在最后
    bc_file = klee_config.get("bc_file")
    if bc_file:
        cmd.append(str(bc_file))
    else:
        raise ValueError("klee.bc_file 未设置，无法执行 KLEE")

    return cmd


def _get_clang_version(clang_exe: str) -> str | None:
    """获取 clang 的主版本号，用于匹配 llvm-link 版本。"""
    try:
        proc = subprocess.run(
            [clang_exe, "--version"], capture_output=True, text=True, timeout=10
        )
        # 匹配 "clang version 14.0.0" 或 "Ubuntu clang version 14.0.0"
        import re
        match = re.search(r"clang version (\d+)", proc.stdout)
        if match:
            return match.group(1)
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _run_compile(*, suite_dir: Path, config: dict, output_dir: Path) -> dict:
    """执行 clang 编译阶段，返回编译结果。

    支持多文件编译：将每个源文件编译为独立的 .bc 文件，
    然后使用 llvm-link 链接为最终的 bitcode 文件。
    """
    compile_config = config["compile"]
    clang_exe = compile_config.get("clang", "clang")
    options = compile_config.get("options", {})
    source_files = compile_config.get("files", [])

    # 提取 -o 参数（最终输出路径）
    output_path = options.get("-o")
    if not output_path:
        return {"ok": False, "return_code": None, "duration": 0,
                "stdout_path": output_dir / "compile_stdout.txt",
                "stderr_path": output_dir / "compile_stderr.txt"}

    timeout = float(config["py_subprocess"]["timeout"])
    compile_stdout_path = output_dir / "compile_stdout.txt"
    compile_stderr_path = output_dir / "compile_stderr.txt"

    # 构建基础选项（排除 -o、-c 和 files）
    base_opts = []
    for option, val in options.items():
        if option in ("-o", "-c"):
            continue
        if isinstance(val, bool):
            if val:
                base_opts.append(option)
        elif isinstance(val, list):
            for item in val:
                base_opts.extend([option, str(item)])
        else:
            base_opts.extend([option, str(val)])

    # 编译：每个文件生成独立的 .bc 文件
    temp_dir = output_dir / "_compile_tmp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    compile_ok = True
    all_return_codes = []
    t_start = time.monotonic()

    try:
        with open(compile_stdout_path, "w", encoding="utf-8") as out, \
             open(compile_stderr_path, "w", encoding="utf-8") as err:

            temp_bc_files = []
            for i, src_file in enumerate(source_files):
                temp_bc = temp_dir / f"part_{i}.bc"
                temp_bc_files.append(temp_bc)

                cmd = [clang_exe] + base_opts + ["-c", "-o", str(temp_bc), str(src_file)]
                print(f"[INFO] 编译 {Path(src_file).name}: {shlex.join(cmd)}")

                try:
                    proc = subprocess.run(
                        cmd, cwd=suite_dir, timeout=timeout,
                        stdout=out, stderr=err, check=False, text=True
                    )
                    all_return_codes.append(proc.returncode)
                    if proc.returncode != 0:
                        compile_ok = False
                        print(f"[ERROR] 编译 {Path(src_file).name} 失败，退出码 {proc.returncode}")
                        break
                except subprocess.TimeoutExpired:
                    print(f"[ERROR] 编译 {Path(src_file).name} 超时: {timeout} 秒")
                    err.write(f"\nCOMPILE_TIMEOUT: {src_file}\n")
                    compile_ok = False
                    break

            if compile_ok and len(temp_bc_files) > 1:
                # 多文件链接：使用与 clang 版本匹配的 llvm-link
                clang_version = _get_clang_version(clang_exe)
                linker = f"llvm-link-{clang_version}" if clang_version else "llvm-link"
                link_cmd = [linker] + [str(f) for f in temp_bc_files] + ["-o", str(output_path)]
                print(f"[INFO] 链接 bitcode: {shlex.join(link_cmd)}")
                try:
                    proc = subprocess.run(
                        link_cmd, cwd=suite_dir, timeout=timeout,
                        stdout=out, stderr=err, check=False, text=True
                    )
                    all_return_codes.append(proc.returncode)
                    if proc.returncode != 0:
                        compile_ok = False
                        print(f"[ERROR] llvm-link 链接失败，退出码 {proc.returncode}")
                except subprocess.TimeoutExpired:
                    print(f"[ERROR] llvm-link 链接超时: {timeout} 秒")
                    err.write(f"\nLLVM_LINK_TIMEOUT\n")
                    compile_ok = False
            elif compile_ok and len(temp_bc_files) == 1:
                # 单文件：直接移动
                shutil.move(str(temp_bc_files[0]), str(output_path))

    except OSError as exc:
        print(f"[ERROR] 编译执行异常: {exc}")
        with open(compile_stderr_path, "a", encoding="utf-8") as err:
            err.write(f"\nCOMPILE_EXCEPTION: {exc}\n")
        compile_ok = False
    finally:
        # 清理临时目录
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    # 确定最终返回值
    return_code = all_return_codes[-1] if all_return_codes else None
    duration = elapsed_seconds(t_start, time.monotonic())

    if compile_ok:
        print(f"[INFO] clang 编译成功，用时 {duration} 秒")
    else:
        print(f"[ERROR] clang 编译失败，用时 {duration} 秒")

    return {
        "ok": compile_ok,
        "return_code": return_code,
        "duration": duration,
        "stdout_path": compile_stdout_path,
        "stderr_path": compile_stderr_path,
    }


def _run_klee(*, suite_dir: Path, config: dict, output_dir: Path) -> dict:
    """执行 KLEE 验证阶段，返回执行结果。"""
    klee_config = config["klee"]
    cmd = _build_klee_cmd(klee_config)

    timeout = float(config["py_subprocess"]["timeout"])

    klee_stdout_path = output_dir / "klee_stdout.txt"
    klee_stderr_path = output_dir / "klee_stderr.txt"

    timed_out = False
    return_code = None
    t_start = time.monotonic()

    try:
        with open(klee_stdout_path, "w", encoding="utf-8") as out, \
             open(klee_stderr_path, "w", encoding="utf-8") as err:
            print(
                f"[INFO] KLEE 运行命令: {shlex.join(cmd)}"
            )
            try:
                proc = subprocess.run(
                    cmd, cwd=suite_dir, timeout=timeout,
                    stdout=out, stderr=err, check=False, text=True
                )
                return_code = proc.returncode
                print(f"[INFO] KLEE 运行结束，退出码 {return_code}")
            except subprocess.TimeoutExpired:
                timed_out = True
                print(f"[ERROR] KLEE 运行超时：{timeout} 秒")
                with open(klee_stderr_path, "a", encoding="utf-8") as err:
                    err.write("\nKLEE_TIMEOUT\n")
    except OSError as exc:
        print(f"[ERROR] KLEE 执行异常: {exc}")
        with open(klee_stderr_path, "a", encoding="utf-8") as err:
            err.write(f"\nKLEE_EXCEPTION: {exc}\n")

    duration = elapsed_seconds(t_start, time.monotonic())

    # 确定 KLEE 输出目录
    klee_options = klee_config.get("options", {})
    klee_output_dir = klee_options.get("--output-dir", str(output_dir / "klee-out"))
    klee_out_path = Path(klee_output_dir)

    return {
        "timed_out": timed_out,
        "return_code": return_code,
        "duration": duration,
        "stdout_path": klee_stdout_path,
        "stderr_path": klee_stderr_path,
        "klee_output_dir": klee_out_path,
    }


def _write_result(
    result_path: Path,
    *,
    compile_result: dict,
    klee_result: dict | None = None,
) -> None:
    """生成 KLEE case 级 result.json。

    使用 analyze_klee_output 提取 KLEE 原始输出中的关键信息，
    写入符合 doc/klee/ 定义的 result.json 格式。
    """
    timed_out = klee_result["timed_out"] if klee_result else False
    klee_duration = klee_result["duration"] if klee_result else 0

    # 分析 KLEE 原始输出
    if klee_result and compile_result["ok"]:
        analysis = analyze_klee_output(
            klee_output_dir=klee_result.get("klee_output_dir"),
            stdout_path=klee_result.get("stdout_path"),
            stderr_path=klee_result.get("stderr_path"),
            timed_out=timed_out,
        )
    else:
        analysis = {
            "conclusion": "INCOMPLETE",
            "statistics": None,
            "warnings": None,
            "error_summary": None,
        }

    result = {
        "conclusion": analysis["conclusion"],
        "return_code": klee_result["return_code"] if klee_result else None,
        "timing": {
            "duration": klee_duration,
            "timed_out": timed_out,
        },
        "statistics": analysis["statistics"],
        "warnings": analysis.get("warnings"),
        "error_summary": analysis["error_summary"],
    }

    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")


def run_klee(*, suite_dir: Path, case: str):
    """执行 KLEE 验证主流程。"""
    check_case_name(case)
    suite_dir = suite_dir.resolve()

    config_filepath = suite_dir / f"{case}.json"
    if not config_filepath.exists():
        print(f"[ERROR] 配置文件不存在: {config_filepath}")
        return

    with open(config_filepath, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 创建输出目录
    output_dir = suite_dir / "output" / "klee" / case
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    # 阶段 1：编译
    print(f"[INFO] 开始编译阶段: case={case}")
    compile_result = _run_compile(suite_dir=suite_dir, config=config, output_dir=output_dir)

    # 阶段 2：运行 KLEE（仅编译成功时）
    klee_result = None
    if compile_result["ok"]:
        print(f"[INFO] 开始 KLEE 验证阶段: case={case}")
        klee_result = _run_klee(suite_dir=suite_dir, config=config, output_dir=output_dir)
    else:
        print(f"[ERROR] 编译失败，跳过 KLEE 验证")

    # 生成 result.json
    result_path = output_dir / "result.json"
    _write_result(result_path, compile_result=compile_result, klee_result=klee_result)

    # 打印结果摘要
    _print_summary(compile_result, klee_result, output_dir)

    # 打印 KLEE 结论
    result_path = output_dir / "result.json"
    if result_path.exists():
        with open(result_path, encoding="utf-8") as f:
            result = json.load(f)
        conclusion = result.get("conclusion", "UNKNOWN")
        stats = result.get("statistics")
        errors = result.get("error_summary")
        if stats:
            print(f"[INFO] KLEE 路径: {stats['explored_paths']} 探索, {stats['completed_paths']} 完成, {stats['generated_tests']} 测试用例, {stats['total_instructions']} 指令")
        if errors:
            print(f"[INFO] KLEE 错误: {errors['total']} 个 ({', '.join(f'{k}={v}' for k, v in errors['by_type'].items() if v > 0)})")
        print(f"[INFO] KLEE 工具执行结果: {conclusion}")


def _print_summary(compile_result: dict, klee_result: dict | None, output_dir: Path) -> None:
    """打印验证结果摘要。"""
    if not compile_result["ok"]:
        print(f"[ERROR] 编译失败，用时 {compile_result['duration']} 秒")
        print(f"[INFO] 编译 stderr 保存至 {compile_result['stderr_path']}")
        return

    if klee_result is None:
        print(f"[INFO] 未执行 KLEE 验证")
        return

    if klee_result["timed_out"]:
        print(f"[ERROR] KLEE 运行超时：{klee_result['duration']} 秒")
        print(f"[INFO] KLEE stderr 保存至 {klee_result['stderr_path']}")
        return

    # 检查 KLEE 输出目录中的错误文件
    klee_out = klee_result["klee_output_dir"]
    if klee_out.exists():
        err_files = list(klee_out.glob("*.err"))
        user_errs = [f for f in err_files if ".user.err" in f.name]
        real_errs = [f for f in err_files if f not in user_errs]
        ktest_files = list(klee_out.glob("*.ktest"))

        if real_errs:
            print(f"[INFO] KLEE 发现 {len(real_errs)} 个错误")
            for err in real_errs:
                print(f"      错误文件: {err.name}")
        if user_errs:
            print(f"[INFO] KLEE 发现 {len(user_errs)} 个 user 警告（不可满足的 assume）")
        if ktest_files:
            print(f"[INFO] KLEE 生成 {len(ktest_files)} 个测试用例")
    else:
        print(f"[WARN] KLEE 输出目录不存在: {klee_out}")

    print(f"[INFO] KLEE 执行用时 {klee_result['duration']} 秒，退出码 {klee_result['return_code']}")
    print(f"[INFO] 结果保存至 {output_dir}")
