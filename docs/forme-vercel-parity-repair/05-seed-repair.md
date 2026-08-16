# Seed repair

The Vercel bootstrap now projects ProposalOps core functional masters plus
the exact FORME parity set. FORME rows use stable `forme-parity:v1:*`
idempotency keys, canonical status/review metadata, source provenance, and
the existing DB-backed synthetic-content mechanism.

No FORME binary is copied into Git, public assets, `/tmp`, or durable source
storage. The synthetic content explicitly identifies itself as an MVP
representation and keeps source identity/hash/path as provenance metadata.

User-edited or dependency-bearing collisions fail closed with a reconciliation
error instead of being silently overwritten or broadly deleted.
