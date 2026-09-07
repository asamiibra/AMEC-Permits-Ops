# AI-D2/D3 platform and interactive methodology metadata

- D0/D1 source: `11490d3844b80aeef23ff5a050dd504e94005a0a`
- D0/D1 tree: `382b524d96017e1e9ebe694032155d07d219823f`
- D2 migration: `ai_d2_execution_ledger_v1` after `step5_content_azure_sql_v2`
- Zero-cost close: feature and external-inference gates default false; all monetary defaults are zero.
- D4 lock: `AI_D4_COMMISSIONING_ID` is required before any hosted inference.
- Frontend: no normal-app AI button is exposed in this tranche.
- Azure mutation/model calls: zero; executable D2 infrastructure was removed.
- Frozen model contract: Azure OpenAI Foundry / gpt-5.1 / 2025-11-13 / Standard / uaenorth
- Deployment: `proposalops-gpt51-methodology-v1`
- Provider endpoint: host-only metadata is recorded after commissioning; no token or key is stored.
- AI UAMI, resource ID, RBAC scope, image digests, revisions, request fingerprints, ledger IDs, usage, and output fingerprints are recorded only when observed; uncommissioned fields remain explicit sentinels.
- This artifact contains metadata only. It contains no source context, prompt, generated draft, token, credential, client identity, or bearer token.
- Verification records: 160 PASS, 0 FAIL.

The detailed records are in the adjacent JSON artifact.
