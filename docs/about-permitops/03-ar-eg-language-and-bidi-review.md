# Arabic (ar-EG) language and BiDi review

## Rendering approach

- The explainer root switches between `lang="en" dir="ltr"` and `lang="ar-EG" dir="rtl"`.
- Every embedded English product, system, status, ID, or technical term in Arabic rich copy uses `LtrTerm`, which renders `<bdi dir="ltr" class="inline-ltr-term">…</bdi>`.
- The lifecycle DOM stays in semantic order 1 → 8. Desktop Arabic mirrors the visual row using CSS direction; mobile remains chronological top-to-bottom.
- Logical CSS properties (`margin-inline`, `padding-inline`, `border-inline`, `inset-inline`) are used in the explainer styles.
- Glossary details and feature groups are keyboard-accessible native controls.

## Mixed-direction review set

| Sentence family | Semantic Arabic order | Visual RTL order | LTR isolation | Punctuation / wrapping |
|---|---|---|---|---|
| `PermitOps` + Arabic + `AMEC` | PASS | PASS — manual browser review required | PASS | PASS |
| `Excel` + `Workflow` | PASS | PASS — manual browser review required | PASS | PASS |
| `Authority AI Precheck` + `Revision` | PASS | PASS — manual browser review required | PASS | PASS |
| `Package` + `Stale` | PASS | PASS — manual browser review required | PASS | PASS |
| `My Work` + Arabic | PASS | PASS — manual browser review required | PASS | PASS |
| `Read-back` + `Portal` | PASS | PASS — manual browser review required | PASS | PASS |
| `RBAC` + `MFA` | PASS | PASS — manual browser review required | PASS | PASS |

The visual rows should be captured at desktop and mobile widths before release. A DOM assertion of `dir="rtl"` alone is not considered sufficient evidence.

