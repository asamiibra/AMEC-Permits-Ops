# Changed files

All changes are isolated primitives, tests, a reproducibility script and evidence. No application route, dependency, migration, production configuration or existing runtime callsite changed.

- `backend/app/services/proposal_document_package.py`
- `backend/app/storage/proposal_source_tree.py`
- `backend/tests/test_proposal_document_package.py`
- `backend/tests/test_proposal_source_tree.py`
- `scripts/proposals_v1/package_probe.py`

Evidence inventory: all files listed in MANIFEST.sha256. Raw client DOCX/images remain outside Git.

Migration files: none.
