# Legacy migration ambiguity register

No destructive legacy backfill is authorized. The following values remain historical or are represented with an explicit safe disposition until an Owner decision or deterministic canonical link exists.

| Proposal ID / ref | Field / concept | Legacy value | Could map to | Why ambiguous | Safe disposition | Owner action |
|---|---|---|---|---|---|---|
| Existing proposals | `ClientAccount` | Existing commercial client | Canonical Party | Client may not be Owner/Applicant and name-only matching is unsafe | Preserve ClientAccount; leave Party link null until resolved | Confirm entity match when needed |
| Existing proposals | `Authority` / `authority_approval` | Free-text authority/approval placeholder | ExternalBody, ServiceType, Jurisdiction | One scalar cannot encode multi-body, service, or jurisdiction intent | Preserve as legacy text; new UX uses structured intent | Decide retirement policy for new drafts |
| Existing proposals | `area` | Generic text/number | Plot/GFA/built-up/net/approved area | Meaning is not encoded | Preserve with `LEGACY_UNSPECIFIED` | Confirm area taxonomy |
| Existing proposals | `duration` / `period` | Commercial text | Service duration estimate | Historical meaning is commercial, not construction or authority timing | Preserve as commercial duration | Confirm optionality by service |
| Existing accepted revisions | Snapshot fields | Historical v1 content | New accepted v2 snapshot fields | Missing property, stakeholder, policy preview, or regulatory intent cannot be invented | Mark not captured / omit from historical schema | Review only if a new revision is created |
| Existing source evidence | `source_reference` | Existing intake/SOR path | Exact DocumentVersion | Some historical artifacts are not deterministically linked | Preserve existing reference and hash; add exact link only when deterministic | Resolve source lineage as needed |

Status: `OWNER_DECISION_PENDING_SAFE_DEFAULT` for policy choices; no fabricated migration values are applied.
