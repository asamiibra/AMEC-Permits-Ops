# Browser evidence

Environment: PostgreSQL synthetic database at migration `0055_bd_proposal_final_hardening`, backend `127.0.0.1:8000`, canonical Vite frontend `127.0.0.1:5173`, Playwright real-stack configuration.

The final targeted command ran three tests and passed all three:

- register `ALL`/lane count reconciliation, non-zero rows, valid detail open, refresh, additional detail states, controlled not-found, and no Safe Recovery;
- New Proposal selection and source-specific panels for Tender Email, Tender Document, Tender Photo / Image, and Client Information;
- Forms-Driven v2 owner workspace preservation.

The intentional not-found API request produces ordinary HTTP 404 resource messages in the browser; no page exception or unexpected application console error was observed.
