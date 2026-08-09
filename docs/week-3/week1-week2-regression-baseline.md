# Week 1–2 Regression Baseline

> **DEMONSTRATION BASELINE — SYNTHETIC DATA — NOT CLIENT APPROVED**

The Week 1 and Week 2 baseline was rerun before the Week 3 decision layer. `make migrate`, `make seed`, `make test`, and `make spike` completed successfully. Backend regression remained green at 18 pre-Week-3 tests; the synthetic Week 2 harness reported 17 documents, classification agreement 1.00, critical-candidate agreement 1.00, zero wrong candidates, median verification 18 seconds, and 14 GOOD / 3 POOR evidence items. No real systems or documents were used.

# Week 3 backend regression adds eight governance, adjudication, threshold, baseline, sign-off, and safety tests. Frontend Vitest and production build also pass.
