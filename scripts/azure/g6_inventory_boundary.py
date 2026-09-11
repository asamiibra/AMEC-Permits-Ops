#!/usr/bin/env python3
"""Capture and validate the G6 qualification resource boundary.

The inventory is resource metadata only. It does not read databases or
application content and it never mutates Azure.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess


def _run_az(*args: str) -> object:
    result = subprocess.run(
        ["az", *args, "-o", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def capture(output: Path, subscription: str | None) -> None:
    args = ["resource", "list", "--query", "[].{id:id,name:name,type:type,resourceGroup:resourceGroup}"]
    if subscription:
        args[2:2] = ["--subscription", subscription]
    resources = _run_az(*args)
    payload = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "G6_DO_NOT_TOUCH_RESOURCE_INVENTORY",
        "subscription": subscription,
        "resources": sorted(resources, key=lambda item: item["id"]),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate(do_not_touch: Path, qualification_resources: Path) -> None:
    protected = {
        item["id"].lower()
        for item in json.loads(do_not_touch.read_text(encoding="utf-8"))["resources"]
    }
    qualification = {
        item["id"].lower()
        for item in json.loads(qualification_resources.read_text(encoding="utf-8"))["resources"]
    }
    collisions = sorted(protected & qualification)
    if collisions:
        raise SystemExit("G6 qualification resource collision:\n" + "\n".join(collisions))
    print(json.dumps({"qualification_resource_collisions": 0, "validated_resources": len(qualification)}))


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    capture_parser = subparsers.add_parser("capture")
    capture_parser.add_argument("--output", type=Path, required=True)
    capture_parser.add_argument("--subscription")
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--do-not-touch", type=Path, required=True)
    validate_parser.add_argument("--qualification-resources", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "capture":
        capture(args.output, args.subscription)
    else:
        validate(args.do_not_touch, args.qualification_resources)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

