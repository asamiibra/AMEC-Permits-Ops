# Resolver and Administration parity

The backend resolver continues to select only active records with
`needs_review=false`, current reviewed versions, and valid bindings. The
targeted repair test proves the seven FORME Needs Review identities are absent
from normal `PERMIT / AVAILABLE` candidates while the seven Current identities
remain eligible candidates.

Dashboard and Administration use the same master-content projection and
DocumentVersion pointer. Deployed Admin parity is a post-deployment gate and
must be recorded after the repaired SHA is live.
