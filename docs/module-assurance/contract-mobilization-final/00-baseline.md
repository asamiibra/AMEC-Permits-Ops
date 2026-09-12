# Contract & Mobilization final assurance baseline

This bounded repair starts from protected `main` at commit `421574ae85ef380778be0f975b9f0f12ff7cedc6`, tree `1cb74f41fe67ceec0fbf5781f5263673508eaacb`. The branch is `module/contract-mobilization-final-assurance-v2`; the historical source branch is preserved at `module/contract-mobilization-production-closure` / `aa8d6afec34f127face91113b813e5bd71dd6aa0`.

Scope is the Contract & Mobilization module, its shared authorization/control seams, tests, and evidence. Azure G8, production, DNS, production databases, real AMEC data, real DSM content, and protected-human business authority are out of scope and were not mutated. No schema change is required by this repair (`SCHEMA_CHANGE_REQUIRED=false`).

The baseline audit reproduced four executable defects: shared review/accept authority, PO/LPO `NOT_ASSERTED` pass-through, generic Contract `CLOSED` mutation, and existence-only `DocumentVersion` binding. The prior G7 tag `v0.1.0-rc.1` remains immutable historical evidence.
