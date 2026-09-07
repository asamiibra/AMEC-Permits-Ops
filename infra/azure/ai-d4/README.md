# AI-D4/D5 isolated Azure contract

This module is the corrected D4/D5 successor to the historical `ai-d2`
module. It provisions one separate AI UAMI named
`uami-proposalops-ai-preprod`, one `uaenorth` Azure OpenAI account, and one
`GlobalStandard` deployment named `proposalops-gpt51-methodology-v1` for
`gpt-5.1`, version `2025-11-13`. Local/API-key authentication is disabled;
the runtime identity receives only the resolved `Cognitive Services OpenAI
User` role on the exact account resource.

`GlobalStandard` means the Azure resource is in `uaenorth` while model
processing is recorded as `GLOBAL_AZURE`; this module does not claim
regional inference. The deployment is synthetic-only and must not receive
real AMEC content.

The `openAiUserRoleDefinitionId` parameter is populated from the current
Azure role-definition lookup immediately before the single authorized
deployment. No model request is made by this module.
