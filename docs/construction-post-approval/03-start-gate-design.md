# Construction Start Gate Design

`ConstructionStartReadiness` is a derived assessment. It checks active `ProjectActivation`, finalized AMEC contract revision, current effective authority-approved design snapshot, current construction design snapshot, required configured party roles, verified authorization grants when a case is bound, and open blocking construction issues.

`ConstructionStartAuthorization` is separate, human-only, idempotent, and immutable in its readiness, party, authorization, activation, contract, authority, and design snapshots. `START` cannot be recorded without it. There is no auto-start path.
