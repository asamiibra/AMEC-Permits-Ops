# Multi-process harness

The closure harness runs two independent OS processes against the same PostgreSQL database and Samba target. It covers same-request intake, same-item promotion, same-target finalization, outbox claiming, and expired-lease recovery. Correctness is database- and storage-enforced; no process-local lock is required.
