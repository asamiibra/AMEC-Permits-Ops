# Changed files

Changes add the Option B editor boundary, its authenticated API routes and the browser editing canvas, alongside isolated preservation primitives, tests, a reproducibility script and evidence. No dependency, migration or production configuration changed.

- `backend/app/services/proposal_document_package.py`
- `backend/app/storage/proposal_source_tree.py`
- `backend/tests/test_proposal_document_package.py`
- `backend/tests/test_proposal_source_tree.py`
- `backend/app/services/proposal_editor_model.py`
- `backend/app/api/proposal_editor_routers.py`
- `backend/tests/test_proposal_editor_model.py`
- `backend/app/main.py` (router registration)
- `frontend/src/ProposalDocumentEditor.tsx`
- `frontend/src/ProposalsContracts.tsx` (editor route)
- `frontend/src/proposal-realignment.css` (editor presentation)
- `scripts/proposals_v1/package_probe.py`

Evidence inventory: all files listed in MANIFEST.sha256. Raw client DOCX/images remain outside Git.

Migration files: none.
