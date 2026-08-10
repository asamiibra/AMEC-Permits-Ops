# Browser regression

Executed from `frontend/`:

```text
npx playwright test browser-e2e/issues-deeplink-final.spec.ts --reporter=line
4 passed
```

Coverage includes the Issue list routes, role-aware Proposal/Permit targets, focus banner, filtered Back to Issues, hard refresh, clean copy, cross-project 409 protection, and mobile overflow. Frontend unit tests pass 24/24 and the production TypeScript/Vite build passes.

The browser run was repeated against the local PostgreSQL 16 `permitops_test` database after applying the current migration head; it also passed 4/4.
