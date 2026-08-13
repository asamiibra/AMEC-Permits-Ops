# Source Evidence Reconciliation

The authority-approved design snapshot captures the approved baseline, pinned baseline members, exact rendition/document IDs, approval lineage references, authority state, effective dates, and a deterministic snapshot hash. The construction design snapshot then pins that authority snapshot and the exact member set used for execution.

Authority notifications and inspections are evidence states. `PREPARED` does not mean sent; `SENT` requires an external reference and optional evidence document; an authority inspection is distinct from an internal site inspection. Authority findings link to canonical `AuthorityCaseFinding`.

No Synology or live authority event was used in this verification. Real SOR/portal provenance remains an external deployment gate.
