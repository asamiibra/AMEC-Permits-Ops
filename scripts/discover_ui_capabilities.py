"""Reconstruct API/UI discovery from source; never infer acceptance from a match.

Run before ui-conformance:prepare. A source reference is a candidate exposure,
not proof of reachability, authorization, successful mutation, or browser QA.
"""
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/ui-conformance"


def literal(node):
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return None


def discover():
    frontend = {str(p.relative_to(ROOT)): p.read_text() for p in sorted((ROOT / "frontend/src").rglob("*")) if p.suffix in {".ts", ".tsx"}}
    capabilities = []
    for file in sorted((ROOT / "backend/app/api").rglob("*.py")):
        source = file.read_text()
        tree = ast.parse(source)
        prefixes = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name) and node.value.func.id == "APIRouter":
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        prefixes[target.id] = next((literal(k.value) for k in node.value.keywords if k.arg == "prefix"), "") or ""
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute) or dec.func.attr not in {"get", "post", "put", "patch", "delete"} or not dec.args:
                    continue
                suffix = literal(dec.args[0])
                if not isinstance(suffix, str):
                    continue
                router = dec.func.value.id if isinstance(dec.func.value, ast.Name) else ""
                endpoint = prefixes.get(router, "") + suffix
                segments = re.split(r"\{[^}]+\}", endpoint)
                candidates = []
                for filename, text in frontend.items():
                    # Require every static route segment, in order, on one line.
                    pattern = ".*".join(re.escape(s) for s in segments if s)
                    for line_no, line in enumerate(text.splitlines(), 1):
                        if pattern and re.search(pattern, line):
                            candidates.append({"file": filename, "line": line_no})
                identity = f"{file.relative_to(ROOT)}:{router}:{dec.func.attr}:{endpoint}"
                capabilities.append({
                    "capability_id": hashlib.sha256(identity.encode()).hexdigest()[:16],
                    "domain": file.stem.removesuffix("_routers"), "method": dec.func.attr.upper(),
                    "endpoint": endpoint, "service": node.name, "source_file": str(file.relative_to(ROOT)), "source_line": node.lineno,
                    "business_meaning": None, "legitimate_personas": [], "authority_level": None,
                    "mutation": dec.func.attr != "get", "protected_action": None,
                    "frontend_candidates": candidates, "classification": None,
                    "classification_rationale": None, "current_exposure_state": "SOURCE_REFERENCE_REQUIRES_REVIEW" if candidates else "NO_STATIC_REFERENCE",
                    "desired_exposure_state": None, "final_canonical_route": None, "browser_test_evidence": [],
                })
    routes = []
    for filename, source in frontend.items():
        for line_no, line in enumerate(source.splitlines(), 1):
            for match in re.finditer(r"[\"'`](/(?:[a-zA-Z][^\"'`\s<>]*|))[\"'`]", line):
                route = match.group(1)
                if route.startswith(("/api", "/health", "/mock-authority")):
                    continue
                routes.append({"route": route, "file": filename, "line": line_no, "classification": None})
    return capabilities, routes


if __name__ == "__main__":
    capabilities, routes = discover()
    OUT.mkdir(parents=True, exist_ok=True)
    provenance = {"entry_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "generator": "scripts/discover_ui_capabilities.py", "evidence_scope": "STATIC_DISCOVERY_ONLY"}
    for name, payload in {
        "backend-ui-capability-ledger.json": {**provenance, "capabilities": capabilities, "total_discovered": len(capabilities), "unclassified": len(capabilities), "verdict": "REQUIRES_ADJUDICATION"},
        "source-route-discovery.json": {**provenance, "references": routes, "distinct_route_patterns": len({r['route'] for r in routes})},
    }.items():
        (OUT / name).write_text(json.dumps(payload, indent=2) + "\n")
    print(f"Discovered {len(capabilities)} API capabilities and {len(routes)} UI route references. Classification and browser proof remain required.")
