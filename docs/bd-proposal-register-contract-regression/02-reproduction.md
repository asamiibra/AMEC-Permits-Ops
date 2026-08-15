# Reproduction

1. Start the synthetic PostgreSQL backend on port 8003 without adding `http://127.0.0.1:5179` to its frontend-origin allowlist.
2. Start Vite on port 5179 with `VITE_API_URL=http://127.0.0.1:8003`.
3. Open `/opportunities` in the in-app browser.
4. The browser sends `OPTIONS /api/bd/proposals?q=&lane=ALL`.
5. The backend responds HTTP 400 `Disallowed CORS origin`; the browser surfaces `Failed to fetch`.

Direct GET evidence from the same backend: HTTP 200, JSON length 12062, correlation ID `908baba3-27ce-4b33-9a27-7dd7f4bb7a51`, `count=2`, and lane counts `ALL=2`, `NEED_ACTION=2`, `AUTHORITY_REVIEW=0`, `READY_CLOSE=0`.
