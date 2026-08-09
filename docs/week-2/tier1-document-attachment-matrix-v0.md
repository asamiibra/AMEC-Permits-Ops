# Tier 1 document and attachment matrix v0

Status: PROVISIONAL SYNTHETIC CONFIGURATION. The seeded corpus is a development fixture, not an authoritative checklist.

| Attachment category | Required state | Allowed document types | Multiple | Language / format note |
|---|---|---|---|---|
| TITLE_DEED | REQUIRED | TITLE_DEED | No | Arabic or bilingual PDF |
| OWNER_ID | REQUIRED | OWNER_QID | No | Arabic or bilingual PDF |
| AUTHORIZATION | CONDITIONAL | AUTHORIZATION | No | Review signatory authority |
| SURVEY | REQUIRED | SURVEY_PLAN, COORDINATE_REPORT | Yes | PDF |
| DRAWINGS | REQUIRED | DRAWING_SET | Yes | Revision metadata required |
| CIVIL_DEFENCE_NOC | CONDITIONAL | NOC | No | Validity date required |
| COMMERCIAL_REGISTRATION | CONDITIONAL | COMMERCIAL_REGISTRATION | No | Entity-owner cases |

The matrix is configured through attachment categories and requirement rules. Missing evidence blocks readiness; an expired or wrong-project document is not silently accepted.
