# Tests and regression

Final focused command:

`APP_ENV=TEST SYNTHETIC_ONLY=true python3 -m pytest -q backend/tests/test_proposal_document_package.py backend/tests/test_proposal_source_tree.py backend/tests/test_proposal_template_fidelity.py backend/tests/test_document_storage_service.py`

Result: 54 passed, one pytest_asyncio/Python 3.14 deprecation warning, 8.15 seconds, exit 0. Includes new source/package primitive tests plus existing touched-boundary compatibility tests.

`python3 -m alembic heads`: one existing head.
`python3 -m py_compile` on both new modules: pass.
`git diff --check`: pass.

Full backend/frontend/release regression: NOT_RUN. Supported DB: NOT_RUN. Full application browser: NOT_RUN. No PASS seal is possible. New modules are isolated; no routes, existing runtime callsites, dependencies or schema were changed.
