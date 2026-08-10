# Synthetic golden path

The canonical fixture contains one shared Project identity across the seeded
Proposal (`SYN-OPP-0001`), ProposalRevision compatibility chain, Contract
(`SYN-CTR-0001`), ContractRevision and PermitApplication. The focused tests add
a provisional Tender/Proposal source pair, verify read-back and idempotent
promotion, then assert that a second Project is rejected.
