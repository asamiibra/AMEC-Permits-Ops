# Owner Input Required

Software is closed and frozen against the implemented contract. Production content/business approvals remain intentionally open under existing decision IDs; no synthetic content is represented as production.

| Existing decision ID | Pending confirmation | Safe default / impact |
|---|---|---|
| `OFFICIAL_PROPOSAL_TEMPLATE` | Official approved template/content | Synthetic Dashboard template remains visibly pending; no code freeze impact. |
| `OFFICIAL_PROPOSAL_CHECKLIST` | Official approved checklist/content | Synthetic checklist remains visibly pending; no code freeze impact. |
| `PROPOSAL_REFERENCE_POLICY` | Production numbering prefix/padding | `AMEC-SYN-PROP-####` is test-safe; production naming remains Owner-controlled. |
| `PROPOSAL_ACCEPT_AUTHORITY` | Final Owner/commercial authority mapping | Existing authorized commercial default applies in TEST. |
| `PROPOSAL_AUTHORITY_REVIEW_MEANING` | Business meaning of Proposal review | Human Proposal review stays separate from government authority. |
| `PROPOSAL_READY_CLOSE_POLICY` | Ready/Close lane meaning | Lane and commercial outcome remain separate. |
| `PROPOSAL_OUTPUT_FORMAT_POLICY` | Official PDF/DOCX renderer and naming | Synthetic text renderer is explicit and not production-ready. |
| `PROPOSAL_CLOSE_OUTCOME_POLICY` | Final outcome vocabulary/close rules | Typed safe vocabulary is implemented; Owner may refine content. |
| `PROPOSAL_TO_CONTRACT_POLICY` | Handoff trigger/cardinality | Explicit handoff only; no auto-contract behavior. |
| `PROPOSAL_ACCEPT_REQUIRED_FIELDS` | Final required-field policy | Existing validator/safe defaults govern TEST. |
| `REAL_SYNOLOGY_CONNECTION` / production file policy | Real storage, access, and content approval | External verification is blocked; synthetic source evidence remains the only allowed mode. |

Tokens: `BD_PROPOSAL_SOFTWARE_CLOSED_OWNER_INPUT_PENDING`, `BD_PROPOSAL_PRODUCTION_CONTENT_PENDING`, `REAL_SYNOLOGY_VERIFICATION_BLOCKED_EXTERNAL`.
