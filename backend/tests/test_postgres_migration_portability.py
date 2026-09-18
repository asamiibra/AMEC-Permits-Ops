from pathlib import Path


def test_contract_scheduler_seed_is_postgresql_portable():
    source = Path("backend/migrations/versions/contract_reconciliation_scheduler_v1.py").read_text(encoding="utf-8")
    assert "WHERE NOT EXISTS" in source
    assert "CURRENT_TIMESTAMP" in source
    assert "SYSUTCDATETIME" not in source
    assert "IF NOT EXISTS (SELECT" not in source


def test_signatory_authority_index_names_fit_postgresql_identifier_limit():
    source = Path("backend/migrations/versions/governed_signatory_authority_v1.py").read_text(encoding="utf-8")
    assert "ix_signatory_authority_evidence_docver" in source
    assert len("ix_signatory_authority_evidence_docver") <= 63
