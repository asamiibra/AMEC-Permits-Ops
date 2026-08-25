from __future__ import annotations

import argparse
import json
from pathlib import Path

from finalize import run


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--acceptance-result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--contracts-dir", type=Path, default=Path("contracts/amec/phase5"))
    args = parser.parse_args()
    result = run(args.contracts_dir, args.acceptance_result, args.evidence_dir, args.output)
    print(json.dumps({"result": result["summary"]["result"], "acceptance_check_count": result["summary"]["acceptance_check_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
