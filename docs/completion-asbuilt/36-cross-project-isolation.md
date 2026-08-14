# Cross-Project and Building Isolation

Status: IMPLEMENTED_AND_VERIFIED.

Every Completion read/write resolves the case project first, validates executions, properties, assets, snapshots, baselines, revisions, packages, findings, and outcomes against that scope, and rejects mismatched project/building references.
