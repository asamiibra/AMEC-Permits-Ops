# AI-D2/D3 isolated Microsoft Foundry contract

This additive module attaches the dedicated preproduction identity
`uami-proposalops-ai-preprod` to an existing Microsoft Foundry project with
the exact `Foundry User` role at project scope. It intentionally does not
create a model deployment: D3 uses Microsoft Foundry Instant Access in
`westus3` with model `gpt-5-mini`, version `2025-08-07`, through the project
endpoint. Local/API-key authentication remains disabled outside this module.

The module is a source-of-truth access contract, not evidence that the
project is reachable or that a real request has passed. Commissioning must
record the resolved account/project resource IDs, identity IDs, tenant,
endpoint, model/version, role scope, immutable image digest, revision, request
ID, ledger ID, usage, and output fingerprint in the commissioning record.
