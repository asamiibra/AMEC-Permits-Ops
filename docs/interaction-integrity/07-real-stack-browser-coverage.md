# Real-stack browser coverage

The new scenario `frontend/browser-real-stack/stage1-confirm-project-sources.spec.ts` runs without API interception against a seeded temporary SQLite database, FastAPI on port 8000, and Vite on port 5173.

Covered:

- Direct navigation to `/proposals-contracts/{project_id}/project-and-sources`.
- Stage 1 projection and real source links.
- Real POST `confirm-project-sources`.
- Success message and transition to Verify Data.
- Hard refresh with persisted `VERIFY_DATA` and `Verify project data` next action.
- Request evidence showing the command POST and follow-up reads.

The full minimum matrix in the implementation prompt is broader than this passing scenario. It is therefore not represented as complete in the final artifact.
