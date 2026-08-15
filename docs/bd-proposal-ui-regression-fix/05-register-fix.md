# Register fix

`backend/app/api/bd_proposal_routers.py` now exposes one predicate path for the register and returns both `items` and `lane_counts` from the same filtered data model. The response retains compatibility fields (`rows`, `count`, filters, and lane options) and adds `predicate_version: bd-proposal-register-v2`.

Regression coverage verifies `ALL` count equals visible rows and verifies the same relationship for Need Action, Authority Review, and Ready / Close lane requests. The frontend no longer invents zeroes during loading or error.
