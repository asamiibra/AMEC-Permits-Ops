# AMEC display identity reconciliation

The active user-facing organization label is **AMEC Engineering**. It is used by the frontend office pill, the office API, canonical fixture metadata, seed office, synthetic emails, and active configuration.

Historical synthetic identifiers such as `GHCE-2026-*`, `GHCE-APP-*`, legacy fixture aliases, project references, mock filesystem paths, and historical reconciliation evidence are intentionally retained. They are stable synthetic IDs and lineage references, not active company display labels. No blanket rename was performed because it would corrupt the reconciled permit fixture and its backward-compatible aliases.

The active UI/configuration scan and tests distinguish display labels from stable identifiers and historical evidence. The only user-facing organization display label required by this gate is `AMEC Engineering`.
