# Role and RBAC regression

The frontend role matrix remains Owner/System Admin, Business Development, and Engineering. Admin navigation remains restricted to the existing privileged roles. Contract & Mobilization navigation remains visible to the existing commercial/owner roles; direct route presentation does not bypass backend authorization.

Mutation calls remain on the existing endpoints and continue to rely on backend capability checks. In particular, Engineering and Business Development do not gain Contract acceptance, Project Activation, Invoice issuance, or Finance settlement privileges through this IA move.

Evidence:

- Existing backend contract and billing authorization suites remain unchanged and continue to target the canonical API endpoints.
- Browser acceptance verifies Owner sees Admin, Business Development does not, and direct Contract & Mobilization access renders the business workspace without adding Admin access.

ROLE_RBAC_REGRESSION_PASS=1
PROPOSOPS_CONTRACT_FINANCE_ROLE_RBAC_VERIFIED
