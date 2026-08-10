# Project-folder resolution

The synthetic adapter resolves the root from `SynologyProjectBootstrap.root_path`. The configured canonical template is the existing repository structure:

`01_Client`, `02_Property`, `03_Design`, `04_Permits`, `05_Correspondence`

Template version: `SYN-AMEC-PROJECT-FOLDERS-1.0`.

Semantic classes are mapped in `backend/app/services/proposals_sor.py`:

| Semantic class | Configured folder | Used by |
|---|---|---|
| `CLIENT_SOURCE` | `01_Client` | Client List |
| `PROPOSAL_SOURCE` | `03_Design` | Proposal Form |
| `CONTRACT_SOURCE` | `04_Permits` | Contract Form |
| `OPPORTUNITY_SOURCE` | `05_Correspondence` | New Proposal initiating source |

These are synthetic mappings over the repository’s actual configured template. The normal UI never accepts a user-typed path. Missing roots, missing folders, observed-template drift, and path escape attempts block the write.
