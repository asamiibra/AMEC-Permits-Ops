# Entry baseline

Entry was verified before reconciliation from the repository state expected by the brief.

- Branch: `main`
- HEAD and `origin/main`: `789014228bff19e48023b73b0a12b034733b2da9`
- Working tree: clean; no concurrent user change was present.
- Entry Alembic: `0048_billing_invoice_full`; latest entry migration `0048_billing_invoice_full.py`.
- Entry database: local PostgreSQL `permitops_dev`, inspected at the entry schema; entry finance/project counts were zero.
- Runtime: Python 3.14.2; Node v24.13.0; npm 11.6.2.
- SQLite compatibility: repository `DATABASE_URL` override, pytest isolated database.
- PostgreSQL certification database: local PostgreSQL database `permitops_v2_full8`, dedicated for this certification.
- Frontend: Vitest, Vite build, Playwright real-stack config.

The entry count inventory is machine-recorded in `00-entry-baseline.json`. No prior workstream was rebuilt; this wave added only the 0049 billing-v2 seam, surgical test-isolation corrections, frontend display/history changes, and certification evidence.
