import json
from pathlib import Path
import os
import shlex
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


def _container_paths(suite_dir: Path, files: list, includes: list) -> tuple[list[str], list[str], list[str]]:
    """映射套件内路径，并为套件外输入建立只读挂载。"""
    mounts = [f"{suite_dir}:/work"]
    external: dict[Path, str] = {}

    def convert(value, directory=False):
        """将一个宿主路径转换为容器内路径。"""
        path = Path(value)
        path = (suite_dir / path).resolve() if not path.is_absolute() else path.resolve()
        try:
            return "/work/" + path.relative_to(suite_dir).as_posix()
        except ValueError:
            root = path if directory else path.parent
            if root not in external:
                external[root] = f"/inputs/{len(external)}"
                mounts.append(f"{root}:{external[root]}:ro")
            return external[root] if directory else f"{external[root]}/{path.name}"

    return mounts, [convert(value) for value in files], [convert(value, True) for value in includes]


def build_cmd(*, suite_dir: Path, config: dict, output_dir: Path,
              container_name: str | None = None) -> list[str]:
    """根据 case 配置构建包含挂载与路径转换的 Docker 命令。"""
    cpa = config["cpachecker"]
    docker = config["docker"]
    image = docker["image"]
    options = cpa.get("options", {})
    mounts, files, includes = _container_paths(
        suite_dir, _items(cpa.get("files")), _items(options.get("-I"))
    )
    cmd = [docker.get("executable", "docker"), "run", "--rm"]
    if container_name:
        cmd.extend(["--name", container_name, "--label", "verify-ip.tool=cpachecker"])
    if hasattr(os, "getuid") and hasattr(os, "getgid"):
        cmd.extend(["--user", f"{os.getuid()}:{os.getgid()}", "--env", "HOME=/tmp"])
    for mount in mounts:
        cmd.extend(["-v", mount])
    for argument in _items(docker.get("arguments")):
        cmd.append(str(argument))
    cmd.append(image)

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
        """规范化布尔 property 以及镜像内标准配置路径。"""
        if isinstance(value, bool):
            value = str(value).lower()
        text = str(value)
        if key == "-config" and not text.startswith("/"):
            name = text.removeprefix("config/").removesuffix(".properties")
            return f"/cpachecker/config/{name}.properties"
        if key == "-spec" and not text.startswith("/"):
            name = text.removeprefix("config/specification/")
            return f"/cpachecker/config/specification/{name}"
        return text

    for key, value in options.items():
        if key in ("-I", "-D") or value is False or value is None:
            continue
        option = aliases.get(key, key)
        if key == "-setprop" and isinstance(value, dict):
            for prop, prop_value in value.items():
                cmd.extend([option, f"{prop}={option_value(key, prop_value)}"])
        elif isinstance(value, bool):
            cmd.append(option)
        else:
            for item in _items(value):
                cmd.extend([option, option_value(key, item)])

    container_output = "/work/" + output_dir.relative_to(suite_dir).as_posix()
    return cmd + ["--output-path", container_output] + files


def run_cpachecker(*, suite_dir: Path, case: str):
    """覆盖执行一个 case，并保存 stdout、stderr、工具产物和简要结果。"""
    check_case_name(case)
    suite_dir = suite_dir.resolve()
    with open(suite_dir / f"{case}.json", encoding="utf-8") as f:
        config = json.load(f)
    if not config.get("docker", {}).get("image"):
        raise ValueError("配置缺少 docker.image")
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
    container_name = f"verify-ip-cpa-{os.getpid()}-{time.time_ns()}"
    cmd = build_cmd(
        suite_dir=suite_dir,
        config=config,
        output_dir=tool_dir,
        container_name=container_name,
    )
    timeout = float(config.get("py_subprocess", {}).get("timeout", 600))

    timed_out = False
    launch_error = False
    return_code = None
    start = time.monotonic()
    try:
        print(
            f"[INFO] subprocess.run(cmd=[{shlex.join(cmd)}], cwd='{shlex.quote(str(suite_dir))}', "
            f"timeout={timeout}, stdout='{shlex.quote(str(stdout_path))}', stderr='{shlex.quote(str(stderr_path))}')"
        )
        with open(stdout_path, "w", encoding="utf-8") as out, open(stderr_path, "w", encoding="utf-8") as err:
            try:
                proc = subprocess.run(cmd, cwd=suite_dir, timeout=timeout, stdout=out, stderr=err, check=False, text=True)
                return_code = proc.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                cleanup = [
                    config.get("docker", {}).get("executable", "docker"),
                    "rm", "-f", container_name,
                ]
                subprocess.run(
                    cleanup,
                    cwd=suite_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=15,
                    check=False,
                )
            except OSError as exc:
                launch_error = True
                err.write(f"无法启动容器命令：{exc}\n")
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
