# AI-D2/D3 isolated Azure contract

This additive module is intentionally separate from the historical
`infra/azure/main.bicep`. It provisions one user-assigned identity named
`uami-proposalops-ai-preprod`, one `uaenorth` Azure OpenAI account, and one
`Standard` deployment named `proposalops-gpt51-methodology-v1` for model
`gpt-5.1`, version `2025-11-13`. Local/API-key authentication is disabled and
the identity receives only the `Cognitive Services OpenAI User` role on the
exact account resource.

The module is a source-of-truth contract, not evidence that the deployment is
commissioned. Commissioning must record the resolved resource, client,
principal, tenant, endpoint, model/version, capacity, and role assignment in
the tranche verification record before `AI_ENABLED=true` is accepted.
