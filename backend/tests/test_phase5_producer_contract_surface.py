from __future__ import annotations

import json
from pathlib import Path

from scripts.phase5.producer_contract_audit import audit
from scripts.phase5.registry import EVIDENCE_PRODUCERS, PRODUCER_RESULT_CONTRACTS


def test_every_registered_producer_has_a_closed_contract_and_writer():
    result = audit(Path(__file__).resolve().parents[2])
    assert result["producer_registry_count"] == len(EVIDENCE_PRODUCERS)
    assert result["producer_without_writer_count"] == 0
    assert result["producer_assertion_path_not_contracted_count"] == 0
    assert result["producer_contract_surface_audit"] == "PASS"


def test_every_contract_path_uses_closed_type_vocabulary():
    vocabulary = {"integer", "number", "string", "boolean", "array", "object"}
    assert all(spec.get("type") in vocabulary for contract in PRODUCER_RESULT_CONTRACTS.values() for spec in contract["required_paths"].values())


def test_diagnostic_fixture_is_machine_readable_when_present():
    path = Path("artifacts/phase5-r3r1r5-current-evidence-diagnostic.json")
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["assertion_entry_count"] == 300
        assert payload["producer_count"] >= 25
