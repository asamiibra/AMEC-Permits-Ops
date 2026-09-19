"""Audit/reconcile the four active Proposal V1 records.

The command is dry-run by default.  ``--apply`` invokes the same governed
source regeneration endpoint used by the browser, so historical revisions are
retained and only records that fail the canonical audit are regenerated.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

from starlette.requests import Request

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.api.proposal_source_routers import CANONICAL_AUDIT_REFERENCES, CanonicalAuditPayload, canonical_audit_regenerate
from backend.app.db import SessionLocal
from backend.app.models import Role


def _request() -> Request:
    request = Request({"type": "http", "method": "POST", "path": "/api/proposals/sources/canonical-audit/regenerate", "headers": [], "client": ("canonical-audit", 0), "server": ("canonical-audit", 0), "scheme": "http"})
    request.state.correlation_id = f"proposal-v1-canonical-audit:{uuid4()}"
    return request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="regenerate records that fail the audit")
    parser.add_argument("--reference", action="append", dest="references", help="exact Proposal reference; repeatable")
    parser.add_argument("--output", default="artifacts/proposal-v1-canonical-audit.json")
    args = parser.parse_args()
    references = args.references or list(CANONICAL_AUDIT_REFERENCES)
    with SessionLocal() as db:
        result = canonical_audit_regenerate(CanonicalAuditPayload(references=references, apply=args.apply), request=_request(), db=db, role=Role.SYSTEM_ADMIN)
    result["deployment"] = {
        "DEPLOYED_BACKEND_SHA": os.getenv("RELEASE_SHA", "UNKNOWN"),
        "CURRENT_PR_HEAD": os.getenv("CURRENT_PR_HEAD", "UNKNOWN"),
        "SCANNED_PDF_VISION_DEPLOYED": os.getenv("SCANNED_PDF_VISION_DEPLOYED", "UNKNOWN"),
    }
    destination = ROOT / args.output if not Path(args.output).is_absolute() else Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not result.get("before", {}).get("missing_references") else 2


if __name__ == "__main__":
    raise SystemExit(main())
