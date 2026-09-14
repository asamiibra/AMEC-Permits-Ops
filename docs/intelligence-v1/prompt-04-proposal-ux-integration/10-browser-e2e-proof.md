# Browser E2E proof

Spec: `frontend/browser-e2e/proposal-intelligence-ux.spec.ts`.

Covered journeys:

- canonical `/proposals` and legacy `/opportunities` resolve to one Proposal Register;
- direct `/proposals/:proposalId` renders the five-stage workspace and asks for human confirmation before acceptance;
- `/proposals/new` renders source-first choices and remains usable at desktop, tablet, and mobile widths;
- fake AI controls are absent;
- horizontal overflow is absent;
- serious/critical Axe violations are absent.

The exhaustive universal UI conformance crawl also passed: 66 material routes, 312 route/persona/viewport results, zero exact gaps, zero serious/critical Axe findings, zero console errors, zero failed requests, and zero horizontal-overflow results.

The run used deterministic browser API interception only. It did not use production data and did not mutate a live system.
