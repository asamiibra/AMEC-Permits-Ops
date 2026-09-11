# G5 Business V1 residual closure

Status: `G5_BUSINESS_V1_CODE_FROZEN=true`

The accepted V1 business path is frozen on the G4 release line. Client RFP intake uses `Opportunity -> Proposal`; no duplicate Tender domain is introduced. Procurement/vendor tendering is formally deferred by this master prompt.

Billing preserves the implemented invoice and receivable core. Receivable aging is derived from issued amount, verified allocation, and a valid due basis. Tax, credit-note policy, collections actions, production numbering, template, financial-account, issue-authority, and final settlement remain explicitly owner-policy or later-closeout boundaries. The supplied billing example is treated as sample-only; no real bank data is copied into code, fixtures, or evidence.

Finance/Billing is discoverable at `/billing`. The former `/admin/invoices` paths are compatibility redirects to the canonical billing workspace.

## Launch scope and classifications

The minimum V1 report surfaces are proposal pipeline, contract/project status, regulatory/submission status, billing/receivables aging, construction/completion/closeout, work/exception queue, and audit/export. No speculative analytics were added.

Non-launch integrations are explicitly deferred with `DEFERRED_OWNER_ACCEPTED=true` in this closure record: procurement tendering, authority portal automation, real Synology verification, external email delivery, bank/ERP/GL settlement, and payment verification as settlement. Existing UI safety language does not imply that those integrations are live.

The 66-route audit classifies 21 routes as `PRODUCTION`, 24 as `ADMIN_INTERNAL`, 0 as `TEST_ONLY`, and 21 as `HISTORICAL_REMOVE`. Historical routes are retained only for compatibility/evidence and are not part of the normal-user business navigation.

Canonical terminology is preserved: Azure SQL is structured operational truth; Synology is the authoritative source-document repository; Content Library is a governed discovery/reuse projection; and lineage is `Source -> Observation -> Human Verification -> VerifiedAssertion -> typed projection`.

## Browser and accessibility support

V1 acceptance targets a modern Chromium-based desktop browser and responsive web use at the evidenced 1280px desktop and 390px mobile viewports. Firefox-specific, WebKit/Safari-specific, and native mobile-shell behavior are not certified in this V1 closure. Accessibility smoke/conformance evidence reports zero serious or critical axe findings, zero horizontal overflow at the representative widths, and passing current-material-route checks. Browser evidence reports 5 readiness tests and 108 full frontend tests passing.

Machine-readable evidence is in `artifacts/business-v1-closure/closure-status.json`.
