from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PHASE5_PYTHON_PATHS = [
    ROOT / "backend/app/main.py",
    ROOT / "backend/app/api/phase5.py",
    ROOT / "backend/app/schemas/classifier_v2.py",
    ROOT / "backend/app/services/classifier_v2.py",
    *sorted((ROOT / "backend/tests").glob("test_phase5_*.py")),
    *sorted((ROOT / "scripts/phase5").glob("*.py")),
]


def _findings():
    boolean = []
    null = []
    for path in PHASE5_PYTHON_PATHS:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=path.as_posix())
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and len(node.args) == 1):
                continue
            argument = node.args[0]
            if node.func.attr == "is_" and isinstance(argument, ast.Constant) and isinstance(argument.value, bool):
                boolean.append((path.relative_to(ROOT).as_posix(), node.lineno))
            if node.func.attr in {"is_", "is_not"} and isinstance(argument, ast.Constant) and argument.value is None:
                null.append((path.relative_to(ROOT).as_posix(), node.lineno))
    return boolean, null


def test_phase5_descendant_python_has_no_boolean_or_null_portability_findings():
    boolean, null = _findings()
    assert boolean == []
    assert null == []
    print(f"PHASE5_DESCENDANT_PYTHON_PATH_COUNT={len(PHASE5_PYTHON_PATHS)}")
    print("PHASE5_DESCENDANT_BOOLEAN_PORTABILITY_FINDING_COUNT=0")
    print("PHASE5_DESCENDANT_NULL_PREDICATE_FINDING_COUNT=0")
