import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[2]))
from core.cpachecker.run_cpachecker import run_cpachecker


def main() -> int:
    parser = argparse.ArgumentParser(description="通过 Docker 执行 CPAchecker 验证")
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--case", required=True)
    args = parser.parse_args()
    try:
        run_cpachecker(suite_dir=args.suite, case=args.case)
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
