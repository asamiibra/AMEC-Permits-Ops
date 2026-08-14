# Migration determinism root cause

0050 imported the current ORM Base and created its table set from mutable metadata. Current models already contained construction_inspections.idempotency_key, its index, and its unique constraint, so a fresh database received them during 0050 and 0051 then attempted to add the same historical change.

The Completion-relevant repaired set is 0044, 0048, 0049, 0050, 0051, and 0052. A full-directory scan still identifies pre-0044 legacy ORM-bootstrap patterns in 0001–0009, 0011–0018, 0037–0043, and 0045–0047. Those are pre-existing outside the narrow Completion repair boundary and are explicitly recorded, not hidden.

0050 now uses frozen static DDL and omits the 0051 idempotency objects. 0051 is dialect-safe and conditional for databases that already received old 0050 output. 0052 uses frozen Completion DDL and keeps approved-design baseline_id separate from as_built_baseline_id.
