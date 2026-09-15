"""Emit the executable FastAPI operation -> UI surface census as JSON.

This intentionally inspects the application after router inclusion. It is not
based on filenames and handles FastAPI's included-router candidates.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

# Permit direct execution from the repository root without relying on an
# activated virtualenv's implicit import path.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.app.main import app

CLASSES = (
    "USER_SURFACE_REQUIRED",
    "UI_SUPPORT_API",
    "SYSTEM_ONLY",
    "INTERNAL_ONLY",
    "DEFERRED_AI",
    "LATER_PRODUCTION_GATE",
)


def operations() -> Iterable[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    for registered in app.routes:
        candidates = registered.effective_candidates() if hasattr(registered, "effective_candidates") else (registered,)
        for candidate in candidates:
            route = getattr(candidate, "route", candidate)
            path = getattr(route, "path", None)
            methods = getattr(route, "methods", None)
            if not path or not methods:
                continue
            for method in sorted(methods):
                key = (method, path)
                if key in seen:
                    continue
                seen.add(key)
                yield {"method": method, "path": path, "name": getattr(route, "name", None), "endpoint": getattr(getattr(route, "endpoint", None), "__module__", None)}


def classify(item: dict[str, Any]) -> tuple[str, str]:
    path = item["path"]
    endpoint = item.get("endpoint") or ""
    lower = path.lower()
    if lower in {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"} or lower == "/":
        return "SYSTEM_ONLY", "framework/documentation surface"
    if lower.startswith("/health") or lower.startswith("/ready"):
        return "SYSTEM_ONLY", "runtime health surface"
    if "/api/ai/" in lower or "governed-prefill" in lower or "ai-comments" in lower or "/intelligence/" in lower:
        return "DEFERRED_AI", "AI/intelligence endpoint; UI scope is deferred"
    if re.search(r"/(test|debug|dev|fixture|seed|synthetic)(/|$)", lower) or "test_support" in endpoint:
        return "INTERNAL_ONLY", "test/development support surface"
    if any(token in lower for token in ("/week", "/phase", "/g10", "/acceptance-rehearsal", "/production-readiness", "/qualification", "/migration", "/diagnostic")):
        return "SYSTEM_ONLY", "historical or qualification evidence surface"
    if any(token in lower for token in ("/go-live", "/role-readiness", "/live-readiness", "/external-connection")):
        return "LATER_PRODUCTION_GATE", "readiness or production gate"
    if lower.startswith("/api/"):
        if item["method"] in {"GET", "HEAD"}:
            return "UI_SUPPORT_API", "read model or register consumed by a human workspace"
        return "USER_SURFACE_REQUIRED", "human workflow command or evidence mutation"
    return "SYSTEM_ONLY", "non-HTTP application route"


def main() -> None:
    rows = []
    for item in operations():
        surface_class, basis = classify(item)
        rows.append({**item, "classification": surface_class, "classification_basis": basis})
    counts = {name: sum(row["classification"] == name for row in rows) for name in CLASSES}
    print(json.dumps({
        "document": "AMEC ProposalOps UI product-surface backend census",
        "source": "backend.app.main:app after router inclusion",
        "classification_classes": list(CLASSES),
        "operation_count": len(rows),
        "unclassified_count": sum(row["classification"] not in CLASSES for row in rows),
        "classification_counts": counts,
        "operations": rows,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
