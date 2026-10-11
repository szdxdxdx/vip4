import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[2]))
from core.cbmc.run_cbmc import run_cbmc


def main():
    parser = argparse.ArgumentParser(description="执行 CBMC 验证")
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--case", type=str, required=True)
    args = parser.parse_args()

    try:
        run_cbmc(suite_dir=args.suite.resolve(), case=args.case)
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
