# Week 1 regression baseline

Recorded before Week 2 UI and service extensions on 2026-08-07.

| Check | Result |
|---|---|
| `make migrate` | PASS |
| `make seed` | PASS |
| `make test` | PASS — 7 backend tests |
| `cd frontend && npm test -- --run` | PASS — 1 frontend test |
| `cd frontend && npm run build` | PASS |
| Direct local API/browser smoke | PASS |

The environment did not have a running Docker daemon, so Docker Compose was not used for this baseline. The local SQLite path remained the verification path.
