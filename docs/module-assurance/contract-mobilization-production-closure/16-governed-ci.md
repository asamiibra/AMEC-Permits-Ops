# Governed CI

`.github/workflows/release-critical-gates.yml` uses Ubuntu 22.04, Python 3.12,
Node 22, and a 20-minute backend budget. Its unrestricted `pull_request` trigger
does trigger all four required checks for a PR targeting
`release/production-stabilization-v3`.

CI_STATUS=PASS
CI_RUN_ID=34657737278
CI_RUN_URL=https://github.com/asamiibra/AMEC-Permits-Ops/actions/runs/34657737278
CI_BACKEND_JOB_ID=103453671043
CI_BACKEND_TEST_COUNT=867 passed, 19 skipped, 5 warnings in 481.92s
CI_FRONTEND_REGRESSION=PASS
CI_MIGRATION_HEAD=PASS
CI_POLICY_AND_SECURITY=PASS
CI_SAMBA_CONTRACT_CHECKS=PASS
CI_BACKEND_TIMEOUT=false
RELEASE_GOVERNANCE_DRIFT=false
