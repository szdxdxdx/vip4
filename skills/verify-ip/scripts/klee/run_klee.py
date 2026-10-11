from argparse import ArgumentParser
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[2]))
from core.klee.run_klee import run_klee


def main() -> int:
    parser = ArgumentParser(description="执行 KLEE 验证")
    parser.add_argument("--suite", type=Path, required=True, help="KLEE 验证套件目录")
    parser.add_argument("--case", type=str, required=True, help="case 名称")
    args = parser.parse_args()
    run_klee(suite_dir=args.suite, case=args.case)
    return 0


if __name__ == "__main__":
    sys.exit(main())
