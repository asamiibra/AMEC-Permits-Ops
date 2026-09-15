# Module review ownership

Proposal review is persisted as `ProposalIntelligenceReviewBinding` plus a Proposal-owned `WorkflowTask`. No shared AI queue, persona queue, or global review center was added. The API exposes only Proposal-owned execution, review listing, candidate review, and decision commands.
