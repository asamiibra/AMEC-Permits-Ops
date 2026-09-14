# Candidate concurrency proof

Candidate families use a server-derived family key, a current-only unique index, and a per-family write lock around supersession and insertion. Superseded rows remain historical; exactly one row can remain `CURRENT` for a family.
