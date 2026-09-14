# API integration map

P04 uses existing endpoints only; no backend router, model provider, migration, or database table is added for UI state.

| UI area | Existing API contract |
| --- | --- |
| Register | `GET /api/bd/proposals` |
| Create with file source | `POST /api/bd/proposals/intake` |
| Create no-source/client context | `POST /api/bd/proposals` |
| Detail/read-back | `GET /api/bd/proposals/{id}` |
| Editable context | `PATCH /api/bd/proposals/{id}`, `PUT /contact`, `PUT /site-context` |
| Evidence | `POST /sources` |
| Engineering | `POST /technical-assessments`, `POST /scope-confirmations`, `POST /service-eligibility` |
| Commercial | `POST /accept`, `POST /revisions`, `POST /commercial-release` |
| Client response | `POST /distribution`, `/client-responses`, `/acceptance-verification`, `/lpo-reconciliation` |
| Handoff | `GET /handoff/contract`, `POST /handoff/contract-eligibility` |

All requests carry the existing role header adapter. Proposal projections and protected controls remain backend-owned.
