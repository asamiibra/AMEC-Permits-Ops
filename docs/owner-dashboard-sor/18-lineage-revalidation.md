# Lineage and revalidation

Every explicit dependency retains its original bound `DocumentVersion` and creates exact-version `LineageEdge` records. A material current-version change moves the dependency to `NEEDS_REVALIDATION`, records the expected current version, and leaves historical versions and lineage intact. Revalidation advances the bound version and returns the dependency to `CURRENT`.

The focused proof verifies the stale bound version, the new expected version, multiple retained lineage edges, the generated Issue/Work/Notification projections, and the final `CURRENT` state after revalidation. No historical binary is overwritten and no historical lineage is rewritten.
