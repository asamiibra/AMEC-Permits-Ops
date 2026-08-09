# Week 11 entry gate

Decision: **READY_FOR_WEEK11**.

Week 10 status is `READY_FOR_WEEK11`; Golden Path v2 passes; evidence-backed finding closure, precheck correction/revision/recheck, stale-state controls, and the negative G9 gate remain green. Canonical fixture is `PermitOps_Synthetic_MVP_Dataset_v1`, version `1.1.0`, manifest hash `f5eaaf110015e50c5bd8349658e42b3afbc07500199a47b05d45b206c08be08d`. SQLite regression is 56 passed; clean PostgreSQL target regression is 56 passed; frontend tests/build pass; machine final-submit operation is absent.

The Week 10 baseline was rerun before this gate. Docker Desktop is not an acceptance dependency because native PostgreSQL 16 validation is the target. The optional automation branch has no approval evidence and is therefore `NOT_AUTHORIZED_NOT_BLOCKING`.
