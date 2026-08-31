# Regression and closure evidence

Focused checks completed on the reconciled worktree:

- `backend/tests/test_retrieval_quality_step3.py`: Q1–Q16, historical replay,
  conflict/ambiguity, access-before-content, citation/hash, and bounded query
  proof.
- `backend/tests/test_canonical_domain_retrieval.py`.
- `backend/tests/test_owner_dashboard_master_content.py`.
- `backend/tests/test_source_intake_service.py`.

Results: Step 3 quality `4 passed`; canonical/source intake `14 passed`;
dashboard/proposal/contract/permit/preparation `12 passed`; engineering and
dashboard `8 passed`; frontend `38 passed`; frontend production build passed.
The reconciled broad backend run reached `239 passed, 15 skipped, 1 failed`.
The one failure is the existing order-sensitive
`test_dashboard_inputs_are_persistent_and_context_specific` fixture: the same
failure reproduces on the frozen Step 2 worktree at `235 passed, 15 skipped,
1 failed`, while the dashboard test passes in isolation. It is unrelated to
the Step 3 changed paths and is not repaired here.

No frontend or build failure remains. The full backend baseline caveat is
preserved explicitly rather than counted as a Step 3 defect.
