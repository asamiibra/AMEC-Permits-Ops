# Regression and closure evidence

Focused checks completed on the reconciled worktree:

- `backend/tests/test_retrieval_quality_step3.py`: Q1–Q16, historical replay,
  conflict/ambiguity, access-before-content, citation/hash, and bounded query
  proof.
- `backend/tests/test_canonical_domain_retrieval.py`.
- `backend/tests/test_owner_dashboard_master_content.py`.
- `backend/tests/test_source_intake_service.py`.

Results: full backend `246 passed, 15 skipped`; Step 3 retrieval, consumer, and
prefill lineage suites pass; frontend `38 passed`; frontend production build
passes; governed-prefill browser proof `1 passed`; `git diff --check` passes.

The earlier baseline order discrepancy is closed: the dashboard numbering
policy projection is stable and no longer depends on mutated reference-sequence
counters. The broad backend run now passes in one invocation, and the security
matrix covers archived definitions, Needs Review, restricted sources, purpose
capabilities, unauthorized projects, and authorization-before-content.
