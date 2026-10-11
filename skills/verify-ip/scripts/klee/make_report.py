import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))
from core.klee.make_report import make_report


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 KLEE 验证 HTML 报告")
    parser.add_argument("--suite", required=True, type=Path, help="KLEE 验证套件目录")
    args = parser.parse_args()
    make_report(args.suite)
    return 0


if __name__ == "__main__":
    sys.exit(main())
