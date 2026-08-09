# Material Change Contract

`MaterialChangeEvent` records source identity, previous/new version or hash, change type, actor/system, correlation ID, materiality, and metadata. Irrelevant changes are recorded as `NO_MATERIAL_CHANGE`; material changes become `APPLIED` only after deterministic impact evaluation. No event auto-approves a replacement.
