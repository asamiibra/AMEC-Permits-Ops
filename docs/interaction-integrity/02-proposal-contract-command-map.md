# Proposal / Contract command map

| Interaction | Classification | Endpoint / backing read | Disposition |
|---|---|---|---|
| New Proposal + source selection | `FILE_INGESTION` | `POST /api/proposals-main/intake` | Existing local tests and browser coverage pass. |
| KPI and status filters | `QUERY_FILTER` | `/api/proposals-main` | Local UI state over API-derived rows; no business mutation. |
| Proposal Proceed | `DOMAIN_COMMAND` | `POST /api/proposals-main/proposals/{id}/proceed` | Existing command tests pass. |
| Proposal → Contract | `DOMAIN_COMMAND` | `POST /api/proposals-main/proposals/{id}/contract` | Existing command tests pass. |
| Engineering Ready for BD | `DOMAIN_COMMAND` | `POST /api/proposals-main/proposals/{id}/engineering-ready` | Existing command tests pass. |
| Contract → Permit | `DOMAIN_COMMAND` | `POST /api/proposals-main/contracts/{id}/permit` | Existing backend coverage exists; whole-app real-stack proof remains required. |
| Provisional source promotion | `DOMAIN_COMMAND` | promotion endpoint | Existing command path; cross-project negative proof remains required. |

No locally fabricated success should be used for these actions. The shared API client rejects non-JSON and invalid JSON responses and preserves status/path in errors.
