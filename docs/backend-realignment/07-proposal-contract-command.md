# CreateContractFromProposal

`POST /api/proposals/{proposal_id}/contract` resolves the existing Proposal,
its current compatibility-backed ProposalRevision and existing Contract chain.
It validates stage and Project identity, preserves ContractRevision, and
returns a typed 422 when the Proposal is not contract-ready or a typed 409 for
a requested Project mismatch. It does not fabricate client acceptance or
create a parallel contract record on retry.
