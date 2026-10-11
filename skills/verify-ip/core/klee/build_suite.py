import json
from pathlib import Path

from core.ir.make_cases_tmpl import make_cases_tmpl
from core.utils import current_datetime_str, ensure_output_dir


def build_suite(*, ir_dir: Path, suite_dir: Path):
    ir_dir = ir_dir.resolve()
    suite_dir = suite_dir.resolve()
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

    tmpl_text = make_cases_tmpl(ir_dir)
    with open(suite_dir / "cases_tmpl.c", "w", encoding="utf-8") as f:
        f.write(tmpl_text)

    print(f"[INFO] 验证套件已生成：{suite_dir}")
