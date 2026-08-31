# Deployed synthetic fixture plan

Namespace every later fixture with `CL4_` and `source_system=SYNTHETIC_CL4`.
Upsert by the stable canonical reference; never allocate from an ambient
sequence or delete broad tables. Reuse means verify the same canonical ID,
version hash, and fixture manifest before each run. Cleanup, if authorized in a
later environment, is by the exact namespace and recorded fixture IDs.

| Fixture identity | Required lineage | Expected behavior |
| --- | --- | --- |
| `CL4_FORM_CURRENT` | MasterContentItem → current DocumentVersion → provenance | exact reference, current citation |
| `CL4_FORM_HISTORY` | same item with V1/V2 and superseded V1 | normal V2; explicit V1 replay |
| `CL4_REPORT`, `CL4_ENGINEERING_WORK` | canonical Master Content current versions | domain retrieval and current preference |
| `CL4_DEFINITION_GFA` | DefinitionEntry → current DefinitionRevision, alias `GFA` | alias lookup and revision citation |
| `CL4_NEEDS_REVIEW`, `CL4_INACTIVE` | governance/status overlay | visible state; never silently current |
| `CL4_RESTRICTED_SAMPLE` | sensitivity/restricted governance profile | authorized-only, sensitivity surfaced |
| `CL4_PROJECT_A_DOCUMENT` | project-scoped DocumentVersion | authorized project evidence |
| `CL4_PROJECT_B_DOCUMENT` | different project DocumentVersion | wrong-project exclusion |
| `CL4_VERIFIED_ASSERTION` | observation → CURRENT VerifiedAssertion | verified structured fact |
| `CL4_CONFLICT_A/B` | same project/field, distinct CURRENT assertions | both citations, `CONFLICTING`, no merge |
| `CL4_BILINGUAL_LABEL` | bilingual canonical title/reference | Q16 bilingual lookup |

Every row is synthetic, canonical-ID linked, citation-bearing, and expected to
be created only after the future integration branch passes its SQL migration
and runtime identity gates.
