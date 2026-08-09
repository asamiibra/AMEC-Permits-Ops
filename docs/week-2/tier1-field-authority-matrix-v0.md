# Tier 1 field authority matrix v0

Status: PROVISIONAL SYNTHETIC CONFIGURATION. Replace with confirmed municipality and client rules during Phase 0.

| Canonical field | Primary source | Fallback | Criticality | Conflict behavior | Human role |
|---|---|---|---|---|---|
| `PROPERTY.PLOT_NUMBER` | TITLE_DEED | SURVEY_PLAN | CRITICAL | Open conflict | Senior permit reviewer |
| `PROPERTY.PIN` | TITLE_DEED | SURVEY_PLAN | CRITICAL | Open conflict | Senior permit reviewer |
| `PROPERTY.ZONE` | TITLE_DEED | SURVEY_PLAN | MAJOR | Open conflict | Permit reviewer |
| `OWNER.NAME_EN` | OWNER_QID | TITLE_DEED | CRITICAL | Open conflict | Permit reviewer |
| `OWNER.QID` | OWNER_QID | TITLE_DEED | CRITICAL | Open conflict | Permit reviewer |
| `DRAWING.REVISION` | DRAWING_SET | — | MAJOR | Fail drawing control | Technical reviewer |

A field observation is a candidate with raw value, normalized candidate, method, confidence, page, and source region. It is not a canonical fact. A verified assertion is created only by a verification action and keeps a pointer to its source observation.
