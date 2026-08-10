# SOR project-root contract

All lifecycle source writes resolve the same `SynologyProjectBootstrap.root_path` from Project identity. The semantic classes map to the existing configured project folders: CLIENT_SOURCE→01_Client, PROPOSAL_SOURCE→03_Design, CONTRACT_SOURCE and PERMIT_SOURCE→04_Permits, and OPPORTUNITY_SOURCE→05_Correspondence. No new physical folders are invented. Read-back verification, versioning, folder-drift guards, and project-scoped lineage remain mandatory.
