# Persona and access model

| Persona | Visible scope | Internal compatibility role |
| --- | --- | --- |
| Owner | Full navigation and visibility, administration, go-live, all shared records | `SYSTEM_ADMIN` |
| Business Development | AMEC Work, Opportunities, Proposals & Contracts, Issues, Notifications | `COMMERCIAL_APPROVER` |
| Engineering | AMEC Work, Engineering & Closeout, Proposals & Contracts, Reviews, Issues, Notifications | `RESPONSIBLE_ENGINEER` |

The selector exposes exactly the three visible personas. The shared task substrate continues to use existing assistant and role identifiers internally until backend model migration is authorized.
