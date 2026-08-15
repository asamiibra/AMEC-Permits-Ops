# Stage 1 source taxonomy

| Owner action | Semantic class | Existing Proposal required | Evidence rule |
|---|---|---:|---|
| Tender Email | `TENDER_EMAIL_SOURCE` | yes after draft creation | preserve filename/content hash/provenance; candidate extraction stays unverified |
| Tender Document | `TENDER_DOCUMENT_SOURCE` | yes after draft creation | DocumentVersion history and exact source relation |
| Tender Photo / Image | `TENDER_IMAGE_SOURCE` | yes after draft creation | image evidence; no implied OCR certainty |
| Client Information | `CLIENT_SOURCE` | yes after draft creation | link/select Client or enter context; never overwrite canonical Client silently |
| Notes / Client Conversation | note/source context | yes | human-entered provenance; never equivalent to official tender evidence |
| Site / Project Photo | site context source | yes | separate from Tender Photo / Image |
| Client List | client master reconciliation | no Proposal creation | never implicit Proposal source |
| Proposal Form | Engineering preparation artifact | existing Proposal | never generic New Proposal source |
| Contract Form | Contract-owned artifact | existing eligible Contract | never Stage 1 source |
