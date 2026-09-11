# Field Authority Matrix

| Field class | Canonical writer | Content Library/AI behavior | Evidence |
|---|---|---|---|
| AMEC-owned reusable metadata | Owner/System Admin | editable through governed owner routes | master-content RBAC tests |
| Client-provided proposal values | BD/Proposal transaction | remains Proposal data; not library truth | BD Forms v2 tests |
| Authority-only fields | official authority / controlled human flow | no AMEC or AI edit/prefill | `source18.packet_manifest`, adversarial prefill tests |
| Evidence observations | Evidence workflow/human verification | library source may be cited, never asserted as verified evidence | week2/evidence tests |
| Project requirement applicability | Requirements engine/Project | not set by library | requirements/preparation tests |
| Professional approval/sign/stamp/release/submit | authorized professional/authority workflow | AI and Content Library cannot perform | Source18/Engineering negative tests |

The authority rule is fail-closed: blank authority-only fields require explicit NA where packet rules require it, and an AMEC/AI write attempt is rejected.
