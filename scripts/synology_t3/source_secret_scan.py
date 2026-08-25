#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import sys

try:
    from scripts.synology_t3.t3_common import scan_text_tree
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.synology_t3.t3_common import scan_text_tree


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    result = scan_text_tree(args.root.resolve(), excluded_names={".git"})
    print(json.dumps(result, sort_keys=True))
    return int(bool(result["match_count"] or result["errors"]))


if __name__ == "__main__":
    raise SystemExit(main())
