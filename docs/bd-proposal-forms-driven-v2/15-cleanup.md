# Cleanup and test-data disposition

Status: `IMPLEMENTED_AND_VERIFIED`

- Full SQLite and PostgreSQL suites use synthetic data only.
- Generated local Synology proposal-intake files, master-content fixture files, workbook changes, and synthetic document mutations were restored/removed after verification.
- The BD test-support cleanup and focused-test cleanup remove typed v2 companion rows before their parent source evidence/Proposal rows, preserving PostgreSQL FK integrity.
- Browser global teardown archived owner-test master-content/decision artifacts; the final workspace was checked for generated fixture churn before staging.
- No real PII, QIDs, signatures, stamps, IBANs, or real supplied forms were used.

Real Synology status remains separately external: `REAL_SYNOLOGY_VERIFICATION_BLOCKED_EXTERNAL`.
