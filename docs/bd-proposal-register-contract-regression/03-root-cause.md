# Root cause

The development frontend built an absolute API URL from `VITE_API_URL`. When the active browser origin was `http://127.0.0.1:5179`, that cross-origin request required a preflight. The backend allowlist named the default frontend origin but not the active 127.0.0.1:5179 origin, so the preflight returned HTTP 400 `Disallowed CORS origin`. The browser then reported `Failed to fetch`, and the Owner page showed placeholder dashes and no rows.

This was not a stale-process-only condition: the isolated stack reproduced it, the exact failing request and correlation ID were captured, and the backend GET independently returned a valid typed dataset. A second contract issue was also closed: strict validator diagnostics previously leaked `PROPOSAL_REGISTER_CONTRACT_INVALID` into Owner copy.

`PROPOSAL_REGISTER_STALE_PROCESS_ONLY_ASSUMPTION=0`.
