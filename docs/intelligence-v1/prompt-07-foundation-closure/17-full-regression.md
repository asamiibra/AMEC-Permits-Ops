# Full regression

Authoritative P07 regression was executed against implementation SHA
`b21ab2fe5e30e306a9bc40149ba10324f0bebd9b`, tree
`9dd412eaed644cef810b8fad0310451ba35d7390`.

- Collection: 976 unique nodes across 127 SQLite-regression files.
- Sharding: 15 deterministic file-partition shards; heavyweight source-preflight was isolated; Week-45 was grouped with Week-7/8 to preserve its documented synthetic fixture prerequisite.
- Execution: 957 passed, 19 governed skips, 0 failed.
- Coverage: exact executed union 976/976; missing 0; duplicate-only coverage 0; unexpected node IDs 0.
- Native SQL Server module: separately classified and excluded from the SQLite census per the P07 contract.

Machine-readable inventory, shard plan, and aggregate are in `21-backend-test-file-inventory.txt`, `22-backend-nodeid-inventory.*`, `23-backend-shard-plan.json`, and `24-backend-full-regression-aggregate.json`.

`P07_BACKEND_FULL_REGRESSION=PASS`.
