# Backend qualification

`CANDIDATE_SHA=c10e3aac0c47d9d158fffe65b89b5b3ce7fe1cc9`
`CANDIDATE_TREE=d0e4ad97b95fa85cfa7e8149c4640bc07f7f0051`
`MAIN_SHA=594b313a15cc6ade3f0505de395a5817c6337268`
`COMMAND=python3 -m compileall -q backend/app backend/tests; pytest focused suites`
`ENVIRONMENT=local synthetic test harness`
`DB_ENGINE=SQLite for focused API fixtures`
`RESULT=PASS: compileall; PASS: test_contract_mobilization_gap_closure.py (1 passed, 1 warning); PASS: Proposal commercial controls (19 passed, 1 warning)`
`EXIT=0`
`REAL_AMEC_DATA_USED=false`

The full backend, concurrency matrix, and target Azure SQL run were not rerun at this head. Therefore backend qualification is partial and cannot be promoted to production PASS.
