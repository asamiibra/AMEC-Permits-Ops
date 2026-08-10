# ProposalOps UI conformance gate

This is the permanent UI conformance and visual-regression gate for ProposalOps / AMEC. It complements functional and backend tests; it does not replace them.

## Run

From `frontend/`:

```bash
npm run ui-conformance:prepare
npx playwright test browser-e2e/ui-conformance.spec.ts --workers=1
```

The crawl renders every material route from `artifacts/ui-conformance/route-inventory.json` for every applicable persona and for desktop, tablet, and mobile. It writes the required JSON evidence files plus screenshots under `artifacts/ui-conformance/screenshots/`.

The final decision is in `artifacts/ui-conformance/final-result.json`. A release may use `PROPOSALOPS_UI_CONFORMANCE_READY` only when every required gate is true. Any failed, incomplete, or pending gate must remain `PROPOSALOPS_UI_CONFORMANCE_NOT_READY`.

## Oracle and scope

The visual and semantic oracle is ProposalOps / AMEC: AMEC Work, Proposals & Contracts, and persona-specific Issues and Notifications. Permit remains a legitimate downstream domain and is audited in its handoff and workspace contexts. The audit checks route discovery, page contracts, role/action parity, semantic statuses, cross-page truth, text quality, layout, mobile behavior, accessibility, network/console health, and mutation/refresh consistency.

The current browser harness uses deterministic synthetic fixtures so that UI failures are reproducible. The real-stack network/console run remains a separate required execution before a production-ready decision.

## Current status

The latest exhaustive run covered 66 material routes, 104 route/persona combinations, and 312 route/persona/viewport renders. It correctly returns `PROPOSALOPS_UI_CONFORMANCE_NOT_READY` while semantic parity, accessibility/layout, console cleanliness, and real-stack evidence gaps remain open. The artifact, rather than this document, is the source of truth for the latest exact gap list.
