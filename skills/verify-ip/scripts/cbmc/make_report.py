import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2]))
from core.cbmc.make_report import make_report


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 CBMC 验证报告")
    parser.add_argument("--suite", required=True, type=Path, help="CBMC 验证套件目录")
    args = parser.parse_args()

    make_report(args.suite)
    return 0


if __name__ == "__main__":
    sys.exit(main())
