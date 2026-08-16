# Production Browser Smoke

Not executed against a new release. A new READY deployment was not created. The local browser suite executed against the exact candidate and produced `62 passed / 7 failed`; the failures are recorded below and are not silently promoted to Production proof.

Passing local evidence included AMEC branding, Operating Guide, AMEC Work/Issues/Notifications flows, persona behavior, readiness drawer, proposal/contract register tests, universal owner audit, and 312 route/persona/viewport crawl cases with zero crawl console errors and zero network failures.

Known failures:

- `about-explainer.spec.ts`: strict locator ambiguity for duplicated `AMEC Work` text.
- `canonical-controls.spec.ts`: expected `Proposals & Contracts` navigation control is absent on the current branch.
- `e7-e8-expanded.spec.ts`: same current-branch navigation mismatch.
- `proposalops-rebrand.spec.ts`: expected `Proposals & Contracts` shell control and `/permits` redirect are absent on the current branch.
- `proposals-main.spec.ts`: expected `/permits` redirect is absent on the current branch.
- `ui-conformance.spec.ts`: `UI_ACCESSIBILITY_PASS=false`; all other conformance checks passed.

```text
LOCAL_BROWSER_SMOKE_PASS=0
VERCEL_FRONTEND_SMOKE_PASS=0
VERCEL_HOME_ACCEPTANCE_PASS=0
LOCAL_BROWSER_CONSOLE_ERROR_COUNT=0 (crawl)
LOCAL_BROWSER_CRITICAL_NETWORK_FAILURE_COUNT=0 (crawl)
VERCEL_BROWSER_CONSOLE_ERROR_COUNT=UNSET
VERCEL_CRITICAL_NETWORK_FAILURE_COUNT=UNSET
```

The expected UI for the current candidate is defined by the current repository tree and its local browser test gate, not by the older Production alias.
