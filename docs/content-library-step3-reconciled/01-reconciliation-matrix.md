# Step 2 lineage reconciliation matrix

| Compared area | Difference | Classification | Decision |
|---|---|---|---|
| Dashboard routes, four library owners, Admin parity | Accepted Step 2 has the canonical route and owner behavior; sibling Step 2 has different convergence history | `PRODUCT_SURFACE_DIFFERENCE` | Accepted `3ed290c` wins; no dashboard rewrite |
| Master-content, DocumentVersion, DefinitionRevision identity | Same canonical model contract | `SEMANTIC_IMPLEMENTATION_DIFFERENCE` | Accepted Step 2 wins; retrieval references existing IDs |
| Retrieval matching | Historical sibling adds normalized identifiers, exact phrase/term ranking, and deterministic tie-break | `SEMANTIC_IMPLEMENTATION_DIFFERENCE` | Required Step 3 delta applied |
| Retrieval query collection | Historical sibling batches related rows and filters authorization before content access | `SEMANTIC_IMPLEMENTATION_DIFFERENCE` | Required Step 3 delta applied |
| Golden quality harness and closure note | New coverage/evidence only | `TEST_HARDENING_ONLY` / `EVIDENCE_ONLY` | Retained and updated for the accepted baseline |
| Historical consumer-convergence branch | Separate later/parallel consumer binding work, not part of the frozen three-file Step 3 delta | `UNKNOWN` until later reconciliation | Not imported; inventoried for follow-on work |

Rule applied: accepted Step 2 behavior wins wherever a sibling behavior would
change the owner-facing surface or canonical write ownership.
