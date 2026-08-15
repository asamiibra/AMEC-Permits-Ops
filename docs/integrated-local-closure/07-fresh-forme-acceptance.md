# Fresh FORME acceptance

The supplied `FORME.zip` was processed through the local v1.4 disposition manifest on fresh PostgreSQL and local Samba. All 24 items reconciled: 7 current promotions, 7 needs-review promotions, 6 transactional/historical sources, 2 ambiguous blocks, 1 source gap, and 1 reference-only item. Fourteen managed promotions had matching source hash and size. A same-batch rerun was business-idempotent and did not move the source archive.

See `artifacts/integrated-local-closure/forme-fresh-acceptance.json` and `forme-idempotency.json`.
