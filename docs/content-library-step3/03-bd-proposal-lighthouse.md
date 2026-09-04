# BD / Proposal lighthouse

BD Proposal already has real canonical template and checklist consumers. Their business purposes remain `PROPOSAL_TEMPLATE` and `PROPOSAL_CHECKLIST`; no speculative purpose was added.

At configuration/validation time, the Proposal uses the deterministic resolver and receives one exact Master Content item, Document, current DocumentVersion, version number, and hash or a fail-closed status. At human acceptance, `ProposalAcceptedRevision` stores the exact template/checklist references, version IDs, version numbers, and hashes. Accepted output artifacts retain the accepted revision lineage.

Proposal emails, tender documents, tender photos, client information, notes, and site/project photos remain transactional Proposal evidence. They are not Dashboard master content merely because a filename or semantic label resembles a Form.

The Proposal engineering-reference adapter is the small current consumer convergence repaired in Step 3; it now uses the same shared eligibility seam.
