# Real-stack browser E2E

The real frontend, Vite server, FastAPI server, and PostgreSQL `permitops_v2_full8` were run together. The dedicated Playwright spec passed: **1 passed**. It loaded the real Billing list, queried the real communication history endpoint, opened a real invoice detail, checked the communication-history surface, and checked the no-settlement boundary.

Scenario adjudication:

- A activated-project Billing: PASS in the full PostgreSQL Billing lifecycle plus real browser list/detail.
- B pre-activation Billing: PASS by the configurable ContractBillingContext/BillingPlan seam; production Owner policy is not fabricated.
- C project-required blocker: PASS by the default `PROJECT_REQUIRED` ContractBillingContext and explicit issue gate.
- D delivery-based due date: PASS in executable Billing lifecycle and browser-visible due/history surface.
- E ExternalAgreement rejection: PASS in executable negative Billing test; external records are not offered as eligible AMEC contracts.
- F canonical Finding one-truth: PASS in the upstream shared-domain, Permit, Submission, and Engineering link tests; no duplicate finding model exists.

B/C/F were not represented as fabricated browser mutations because the current Owner register has no confirmed production billing-policy choice and real authority integration is unavailable. The browser check is therefore documented together with its executable backend evidence rather than overstated as a real external transaction.
