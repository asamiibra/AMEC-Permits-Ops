# 11 · Immutable PreparationRevision

Status: IMPLEMENTED

Each case preparation revision pins policy version, optional approved design baseline, requirements, evidence, and physical evidence into a canonical PreparationRevision snapshot. Locking computes a SHA-256 snapshot hash and changes the authority state to LOCKED; locked revisions are immutable.
