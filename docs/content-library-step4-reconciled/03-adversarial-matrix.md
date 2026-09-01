# Step 4 adversarial acceptance

The synthetic suite covers unauthorized and wrong-context callers, purpose
misuse, Needs Review and archived masters, restricted samples, superseded and
mismatched versions, stale mapping/release/evidence/assertion state, stale
preview fingerprints, stale draft revisions, duplicate and colliding
idempotency keys, invalid field selections, authority-only/locked/protected
and user-entered field collisions, cross-project evidence, non-DRAFT targets,
tampered request pins, atomic batch rejection, and protected-action side
effects.

The accepted Apply path is idempotent: an identical replay returns its prior
result without another mutation or draft revision; a different request under
the same idempotency key is rejected.
