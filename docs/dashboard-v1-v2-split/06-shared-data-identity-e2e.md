# Shared Data Identity E2E

The split adds no persistence model or migration. Both presentations call the same `/api/master-content` list/detail endpoints and the same version/download/history operations. The focused UI contract renders one synthetic canonical fixture (`id=shared-form-1`, `ref=F-0001`) through V1 and V2 and asserts the same reference appears once in each surface.

The existing canonical master-content and Wave A regression suites cover version lineage, exact `DocumentVersion` source-section pins, resolver identity, and material propagation. The implementation contains no `dashboard_version` data field, V1/V2 model names, or copy migration.

Migration validation was run on a fresh PostgreSQL database through `0036_dashboard_forms_governance_wave_a`; no downgrade or data-copy operation occurred.
