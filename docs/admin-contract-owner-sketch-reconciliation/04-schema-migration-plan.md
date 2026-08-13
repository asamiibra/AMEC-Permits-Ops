# Schema and migration plan

Current repository head is `0044_preparation_submission_loop`; the next migration number is selected from the repository, not assumed from historical notes.

## Planned additive migration

Add only Contract-scoped canonical child tables required by the gap matrix:

- `contract_payment_terms`: exact ContractRevision scope, sequence, raw term text, optional human-verified basis/percentage/fixed amount/currency/trigger/due days/source clause, verification actor/time, status.
- `contract_deliverable_commitments`: ContractRevision scope, sequence/ref/name/description, optional Proposal scope lineage, optional due/trigger description, lifecycle status.
- `contract_client_input_requirements`: ContractRevision scope, sequence/code/title/description, optional Proposal expected-input/assumption/document lineage, required/status, human-controlled source.

Extend `contract_admin_evidence` with `document_version_id` and a normalized source role where the database permits additive nullable columns. Existing string references remain historical and are not promoted to exact LPO evidence without proof.

Add indexes/uniqueness on `(contract_id, revision_id, sequence)` and hard foreign keys to Contract, ContractRevision, ProposalAcceptedRevision where applicable, and DocumentVersion. Do not create ContractCommercialV2, ContractClientCopy, ContractProjectCopy, ContractBillingMilestone, or Invoice tables.

## Backfill policy

Backfill only deterministic existing values. Historical free-text Payment Condition, Deliverables, Documents Needed, Valuation, and LPO references remain raw/needs-review unless source metadata proves their meaning. Finalized history is never rewritten.

## Rollback / round trip

Fresh upgrade, upgrade from the current head, downgrade where repository policy requires, and re-upgrade must preserve all pre-existing Contract, ProjectActivation, Proposal, and Invoice history. A DTO-only Billing context requires no migration.
