import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[2]))
from core.cpachecker.make_report import make_report


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 CPAchecker 验证报告")
    parser.add_argument("--suite", type=Path, required=True)
    args = parser.parse_args()

    make_report(args.suite)
    return 0


if __name__ == "__main__":
    sys.exit(main())
