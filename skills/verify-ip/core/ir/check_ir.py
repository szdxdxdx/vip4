import json
from pathlib import Path



def check_ip_json(ir_dir: Path) -> list[str]:
    ip_json_path = ir_dir / "ip.json"
    if not ip_json_path.is_file():
        return ["ip.json 文件不存在"]

    try:
        value = json.loads(ip_json_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [f"ip.json 读取或解析失败：{exc}"]

    if not isinstance(value, dict):
        return ["ip.json 根节点必须是 JSON object"]
    if "ip" not in value:
        return ["ip.json 缺少字段：ip"]
    if not isinstance(value["ip"], str) or not value["ip"].strip():
        return ["ip.json 字段 ip 必须是非空字符串"]
    return []


def check_ir(ir_dir: Path) -> list[str]:
    ir_dir = Path(ir_dir).resolve()
    if not ir_dir.is_dir():
        error = f"IR 目录不存在或不是目录：{ir_dir}"
        print(f"[ERROR] {error}")
        return [error]

    errors = []
    errors.extend(check_ip_json(ir_dir))
    if not (ir_dir / "cases_tmpl.c").is_file():
        errors.append("cases_tmpl.c 文件不存在")

    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
    else:
        print("[INFO] IR 检查完成，未发现错误")
    return errors
