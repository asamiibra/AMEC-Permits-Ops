# Proposal → Contract lineage

The canonical relationship is `ReferenceNumber.opportunity_id → quotation_id → contract_id`, with `project_id` carried on the same root. The proposal row exposes `related_contract_id` and the Contract row exposes `related_proposal_id`; the Contract row is not linked by display text alone. The existing human transition endpoint remains available at `/api/proposals/{proposal_id}/contract` and the row source action uses the same Contract Form intake boundary.
