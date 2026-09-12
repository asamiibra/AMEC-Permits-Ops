# Requirement reconstruction

The canonical module is Proposal-centric. It reuses the existing Opportunity, Party, Document/Content Library, Contract, and Project contexts and does not introduce duplicate Tender, CRM, Party, Content Library, or Contract engines.

The controlled lifecycle is:

`source intake → source evidence → site/technical assessment → scope confirmed → service eligibility → governed template/checklist → Proposal prepared → revision → review/approval → Proceed → protected commercial release → distribution → client response → acceptance evidence → PO/LPO reconciliation → Contract handoff eligibility`.

Proposal handoff is distinct from Contract acceptance and Project Activation. AI remains assistive only; it cannot accept, release, distribute, verify acceptance, reconcile an LPO, or activate downstream work.

Synthetic qualification fixtures are the canonical resolver targets:

- `SYN-QUAL-PROPOSAL-TEMPLATE-V1`, purpose `PROPOSAL_TEMPLATE`
- `SYN-QUAL-PROPOSAL-CHECKLIST-V1`, purpose `PROPOSAL_CHECKLIST`

Both are synthetic-only, qualification-only, and not real AMEC masters.
