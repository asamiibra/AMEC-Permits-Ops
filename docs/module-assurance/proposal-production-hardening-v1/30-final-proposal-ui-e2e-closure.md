# Final Proposal UI / E2E closure

This is the final exact-head handoff record for PR #48. Historical PR41 evidence remains attached to its historical exact SHA and is not rewritten.

```text
FINAL_RESULT=BLOCKED_EXTERNAL
WORKING_BRANCH=module/opportunity-proposal-client-tender
PR_NUMBER=48
PR_URL=https://github.com/asamiibra/AMEC-Permits-Ops/pull/48
FINAL_BRANCH_SHA=cda88ad150add653362de879262a9de4f3bef0f4
FINAL_BRANCH_TREE=b8cc828112e6d15b9642cbc4272e7702061ab4ba
ENTRY_MAIN_SHA=d92cef6d6fdbb7e4248061ebbcfef30cf2f0011d
ENTRY_MAIN_TREE=04af916251fb2cf92b8575a9e780d35c3322baf8
ENTRY_MERGE_BASE=d92cef6d6fdbb7e4248061ebbcfef30cf2f0011d
ENTRY_AHEAD_OF_MAIN=34
ENTRY_BEHIND_MAIN=0
HISTORICAL_PR41_SHA=dbd54c8e208e7347c959364b0bffd0f513eb81c7
HISTORICAL_PR41_MERGE=e3af5e8d5c8abc996f1039aaae394bb734cc0193
AI_BACKEND_SEMANTICS_CHANGED=false
REQUIRED_OPERATOR_BACKEND_CAPABILITIES=43
FULLY_EXPOSED_REQUIRED_CAPABILITIES=43
PARTIALLY_EXPOSED_REQUIRED_CAPABILITIES=0
UNEXPOSED_REQUIRED_CAPABILITIES=0
FRONTEND_REGRESSION=PASS (25 files, 124 tests)
BACKEND_REGRESSION=PASS (972 passed, 33 skipped, 4 warnings)
PROPOSAL_FOCUSED_BACKEND=PASS (26 passed, 1 warning)
PROPOSAL_CLOSURE_UI=PASS (2 files, 9 focused tests)
FRONTEND_BUILD=PASS
PYTHON_COMPILE=PASS
GIT_DIFF_CHECK=PASS
ACR_API_BUILD=PASS (sha256:a5e680e8af10630e8c2f6dbf5c59f3534b0a6326dadc9c94d0fcdc3e93c3b692)
ACR_WEB_BUILD=PASS (sha256:48c2fe6965be3dda96eb3299c1db4fde10881fb906f6bd11484e0ec8be05cce7)
GOVERNED_MIGRATION=PASS (prop-owner-mig-3ad507d4; final execution succeeded)
OWNER_TEST_API_REVISION=proposalops-api-preprod--0000009
OWNER_TEST_API_STATE=Healthy / Provisioned / HTTP 200 / traffic 0 (direct revision)
OWNER_TEST_WEB_REVISION=proposalops-web-preprod--0000010
OWNER_TEST_WEB_STATE=Healthy / Provisioned / HTTP 200 / traffic 100
OWNER_TEST_RELEASE_SHA=cda88ad150add653362de879262a9de4f3bef0f4
BROWSER_OWNER_SMOKE=PASS (authenticated register, Proposal open, all 7 workspace views)
DIRECT_REVISION_AUTH=BLOCKED_EXTERNAL (Entra redirect URI is registered for the custom domain)
GITHUB_REQUIRED_CHECKS=BLOCKED_EXTERNAL (Vercel frontend rate-limited; Vercel backend deployment failed; samba-contract passed)
OWNER_ACCEPTANCE=PENDING_OWNER_TEST
```

Owner-test URL: https://www.amecidsystem.com/opportunities

The public `www` host is the sanctioned browser entry point. Direct Container Apps revision URLs are retained for exact deployment provenance; their Entra redirect URI is not registered as a user-facing login origin.
