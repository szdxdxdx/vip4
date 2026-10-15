from argparse import ArgumentParser
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[2]))
from core.ir.check_ast import check_ast
from core.ir.make_cases_tmpl import make_cases_tmpl


def main() -> int:
    parser = ArgumentParser(description="检查 contract AST 并生成 cases 模板")
    parser.add_argument("--ir", type=Path, required=True, help="IR 目录")
    args = parser.parse_args()
    ir_dir = args.ir.resolve()
    errors = check_ast(ir_dir)
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1
    (ir_dir / "cases_tmpl.c").write_text(make_cases_tmpl(ir_dir), encoding="utf-8")
    print(f"[INFO] cases_tmpl.c 已生成：{ir_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
