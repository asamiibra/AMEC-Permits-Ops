DO NOT DEPLOY.
AI-D4 OWNER AUTHORIZATION REQUIRED.

# Future AI-D4 target — architecture metadata only

This document is not executable infrastructure. AI-D4 may later commission
one separate user-assigned managed identity, bound only to the API candidate
revision, and one Azure OpenAI / Foundry deployment after explicit Owner
authorization.

- Model: `gpt-5.1`
- Version: `2025-11-13`
- Deployment type: `Standard`
- Region: UAE North (`uaenorth`)
- Model router: disabled
- PTU/provisioned throughput: forbidden for initial commissioning
- Public/API-key credentials: not authorized
- Azure SQL identity: must remain distinct from the future AI identity

AI-D2/D3 creates no identity, resource, role assignment, deployment, ACA
revision, traffic change, or Azure migration.
