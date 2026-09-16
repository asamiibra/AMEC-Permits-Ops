# Editor Option B evidence

The Owner selected `EDITOR_OPTION=B`: the browser is an editing canvas over a
server-owned document model. The browser never parses or serializes DOCX.

`backend/app/services/proposal_editor_model.py` imports the validated package
through `document_map`, gives each node its stable OOXML anchor and XML hash,
and marks complex paragraphs, drawings, embedded media and VML/textbox content
read-only. `editor_diff_to_mutations` refuses topology drift, forged editability
and read-only changes. `tracked_changes` exposes Accept, Edit, Reject and Show
source review actions.

`backend/app/api/proposal_editor_routers.py` exposes authenticated import,
change review, export and true-render preview endpoints. Export always calls
`apply_text_mutations` against the original uploaded package. The renderer is
the host `soffice`/LibreOffice pipeline when available and fails explicitly when
it is not available.

The canvas in `frontend/src/ProposalDocumentEditor.tsx` uses only browser
editing primitives and displays the import/export boundary. It does not claim
WYSIWYG fidelity. The true-render preview is the acceptance surface.

Library decision: no DOCX editor library is used. `EDITOR_LIBRARY=
BROWSER_CONTENTEDITABLE_CANVAS`, `EDITOR_LICENCE=permissive browser platform`,
and `DOCX_IMPORT_OWNED_BY=server`.

The supplied baseline remains SHA-256
`d383cd55ac370cb6793e3481bd60774be6b711237693b41eec5b699bd1edf485`. The
controlled package probe changed only `word/document.xml`; 78 of 79 package
parts and rendered pages 1–11 were unchanged. The full application editor,
source capture, persistence and browser acceptance remain incomplete, so this
branch is not promoted to PASS.
