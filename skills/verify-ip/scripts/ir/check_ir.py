from argparse import ArgumentParser
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[2]))
from core.ir.check_ir import check_ir


def main() -> int:
    parser = ArgumentParser(description="检查完整 IR 是否符合规范")
    parser.add_argument("--ir", type=Path, required=True, help="待检查的 IR 目录")
    args = parser.parse_args()

    errors = check_ir(args.ir.resolve())
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
