# Lineage, search, and AI boundary

Verified current versions emit `MasterContentChangeEvent` and audit events. The current repository has no master-content extraction/index consumer to wire without inventing a second index contract, so this change records the material-change hook and exact version identity for future existing consumers. Engineering Works are not treated as authoritative merely because they were uploaded; their current/verified status remains the eligibility boundary. Professional approval and final submission authority are unchanged.
