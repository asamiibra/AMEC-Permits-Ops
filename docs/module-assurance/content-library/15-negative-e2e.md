# Negative End-to-End Evidence

The negative contract covers:

- invalid category type and reference prefix;
- incompatible module/purpose/content type;
- inactive binding and dependency targets;
- definition/revision collisions;
- incomplete or reversed PAGE_RANGE locators;
- unreviewed, stale, missing-source, restricted and ambiguous content;
- non-owner dependency mutation;
- cross-persona discovery leakage;
- AI assist and authority-only field mutation;
- stale OfficialFormVersion and packet release attempts.

All synthetic negative paths assert the rejection code and durable-state invariant. No production, preprod, Azure, Entra, DSM or real AMEC data is used.
