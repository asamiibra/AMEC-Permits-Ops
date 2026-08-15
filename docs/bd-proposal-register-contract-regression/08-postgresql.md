# PostgreSQL evidence

Fresh database: `proposal_register_contract_regression_20260815`.

- Alembic upgrade reached `0055_bd_proposal_final_hardening`.
- Full backend suite: `215 passed, 2 warnings` in 40.79s.
- No PostgreSQL test failures or errors.
- Warnings are the pre-existing asyncio deprecation and nullable Finding identity warning; neither is a Proposal Register failure.
