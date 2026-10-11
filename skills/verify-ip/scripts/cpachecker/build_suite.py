from argparse import ArgumentParser
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[2]))
from core.cpachecker.build_suite import build_suite


def main() -> int:
    parser = ArgumentParser(description="构建 CPAchecker 验证套件")
    parser.add_argument("--ir", type=Path, required=True)
    parser.add_argument("--suite", type=Path, required=True)
    args = parser.parse_args()

    build_suite(ir_dir=args.ir, suite_dir=args.suite)
    return 0


if __name__ == "__main__":
    sys.exit(main())
