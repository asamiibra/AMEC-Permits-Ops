# Browser acceptance

Dedicated ownership acceptance:

- Admin renders system configuration and has zero rendered Contract/Invoice operational registers.
- Contract & Mobilization renders the canonical Contract register and preserves the controlled accepted-Proposal create boundary.
- `/admin/contracts`, `/admin/invoices`, and `/admin/project-activation` resolve to owning workspaces.
- Finance renders the Finance/Billing surface and no longer uses Admin/Invoices copy.
- Owner/Admin and Business Development navigation visibility remains bounded.
- Home retains seven stages, contextual Finance, and no Finance primary-sidebar entry.

Command run:

```text
npm run browser-e2e -- browser-e2e/domain-ownership-reorganization.spec.ts browser-e2e/home-command-center.spec.ts browser-e2e/workflow-first.spec.ts browser-e2e/canonical-controls.spec.ts browser-e2e/e7-e8-expanded.spec.ts
```

Result after the final route fixes: 34 passed.

BROWSER_ACCEPTANCE_PASS=1
PROPOSOPS_CONTRACT_FINANCE_ADMIN_BROWSER_ACCEPTANCE_PASS
