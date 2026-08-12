# Administration + Contract Owner Session — Entry Baseline

Date: 2026-08-12

The implementation started from clean `main` at the frozen Dashboard v3 / BD Proposal baseline. Existing canonical repositories and primitives were retained: `ClientAccount`, `Project`, `Opportunity`, `ProposalAcceptedRevision`, `Contract`, `ContractRevision`, Dashboard master content, audit, lineage, WorkflowTask, Finding, and NotificationEvent.

Frozen boundaries carried forward:

- `PROPOSAL_ACCEPTANCE_AUTHORITY_PRESERVED`
- `ACCEPTED_PROPOSAL_REVISION_IMMUTABLE`
- `DASHBOARD_CONTRACT_TEMPLATE_CANONICAL_TRUTH_PRESERVED`
- `CLIENT_CANONICAL_TRUTH_PRESERVED`
- `PROJECT_CANONICAL_TRUTH_PRESERVED`
- `MY_WORK_ISSUE_NOTIFICATION_SEMANTICS_PRESERVED`
- `HUMAN_PROJECT_ACTIVATION_AUTHORITY_PRESERVED`

Real Synology remains an external go-live dependency; synthetic verification is explicitly labeled.
