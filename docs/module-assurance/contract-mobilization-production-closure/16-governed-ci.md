# Governed CI

`.github/workflows/release-critical-gates.yml` uses Ubuntu 22.04, Python 3.12,
Node 22, and a 20-minute backend budget. Its unrestricted `pull_request` trigger
does trigger all four required checks for a PR targeting
`release/production-stabilization-v3`.

CI_STATUS=NOT_YET_RUN
CI_BACKEND_TIMEOUT=false
RELEASE_GOVERNANCE_DRIFT=false
