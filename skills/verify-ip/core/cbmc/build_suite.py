import json
import shutil
from pathlib import Path

from core.ir.check_ir import check_ir
from core.utils import current_datetime_str, ensure_output_dir


def build_suite(*, ir_dir: Path, suite_dir: Path):
    ir_dir = ir_dir.resolve()
    suite_dir = suite_dir.resolve()
    errors = check_ir(ir_dir)
    if errors:
        raise RuntimeError("IR 检查失败，无法构建验证套件")
    ensure_output_dir(suite_dir)

    with open(ir_dir / "ip.json", encoding="utf-8") as f:
        ip_data = json.load(f)

    with open(suite_dir / "suite.json", "w", encoding="utf-8") as f:
        data = {
            "suite_created_at": current_datetime_str(),
            "ip": ip_data["ip"]
        }
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    shutil.copyfile(ir_dir / "cases_tmpl.c", suite_dir / "cases_tmpl.c")

    print(f"[INFO] 验证套件已生成：{suite_dir}")
