from argparse import ArgumentParser
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[2]))
from core.klee.build_suite import build_suite


def main() -> int:
    parser = ArgumentParser(description="构建 KLEE 验证套件")
    parser.add_argument("--ir", type=Path, required=True, help="IR 目录（含 contract.json）")
    parser.add_argument("--suite", type=Path, required=True, help="KLEE 验证套件输出目录")
    args = parser.parse_args()
    build_suite(ir_dir=args.ir, suite_dir=args.suite)
    return 0


if __name__ == "__main__":
    sys.exit(main())
