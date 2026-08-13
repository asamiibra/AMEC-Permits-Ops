# Preparation snapshot

`PreparationRevision.case_party_snapshot_id` now pins an immutable `CasePartySnapshot`. Its hashed JSON captures case subject, scoped roles, masked party projections, authorization references/status/scope/evidence pins, regulatory contacts, and capture time. Preparation creation and lock create/audit/lineage the snapshot; the authority snapshot also contains the reproducible party context. Existing policy, requirements, evidence, physical evidence, and approved-design-baseline pins remain intact.
