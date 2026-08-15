# Capability ledger

| Capability | Route/UI effect | Authority |
|---|---|---|
| `BD_PROPOSAL_READ` | Register, detail, validation, outputs | BD/Owner read roles |
| `BD_PROPOSAL_WRITE` | Draft fields, sources, structured context, typed risk/response/outcome | BD write roles |
| `EDIT_TECHNICAL` | Engineering technical preparation only | Responsible Engineer |
| `BD_PROPOSAL_ACCEPT` | Material acknowledgment and human Proposal Accept | Owner/authorized commercial approver |
| `BD_PROPOSAL_OWNER_SETTINGS` | Owner go-live/configuration surface | Owner/System Admin |

Engineering cannot edit commercial fields or Accept. Proposal Accept is not AI-generated and creates no government `AuthorityCase`.
