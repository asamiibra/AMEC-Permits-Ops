# Reproduction

The regression surface was the BD Proposal Register and its canonical `/opportunities` route. Before the fix, the list loaded `data.lane_counts || {}` and rendered missing values as numeric `0`; source-card clicks changed only local selection while the create action always posted JSON to `/api/bd/proposals`; and the detail loader could leave a fragile shell when the route or payload was unavailable.

The first browser fidelity run also exposed an environment mismatch: a Vite process on port 5175 used `VITE_API_URL=http://127.0.0.1:8002`, while the canonical backend was on port 8000. The canonical stack is Vite 5173 with its `/api` proxy to backend 8000. With the source-matched database and canonical stack, valid Proposal routes returned HTTP 200 and rendered without Safe Recovery. An exact React exception stack was not reproducible in the final source-matched run; the audit nevertheless identified unsafe optional display assumptions and stale route/load handling as the render-risk class.

Observed fidelity records included Owner and synthetic Preparation, Accepted, and Contract Handoff cases. The final browser run exercised the PostgreSQL-backed synthetic Preparation and Contract Handoff records, direct refresh, back/forward-compatible route state, and a controlled not-found route.
