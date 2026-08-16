# Icon inventory

Scope: icon presentation only. This inventory records the final rendered icon family and the semantic intent of each replacement. Navigation labels, item order, targets, routes, workflows, and business meaning are unchanged.

## Primary navigation

| Existing surface / label | Final icon | Rendered size | Slot | Stroke | Semantic intent |
| --- | --- | ---: | ---: | ---: | --- |
| Dashboard / Home surface | `House` | 18px | 22px | 1.8 | Home / landing surface |
| AMEC Work | `ListTodo` | 18px | 22px | 1.8 | Prioritized worklist |
| Opportunities | `Target` | 18px | 22px | 1.8 | Commercial opportunity focus |
| Engineering & Closeout | `DraftingCompass` | 18px | 22px | 1.8 | Engineering preparation and closeout |
| Construction | `HardHat` | 18px | 22px | 1.8 | Construction work context |
| Completion / As-Built | `BadgeCheck` | 18px | 22px | 1.8 | Verified completion outcome |
| Permit Portfolio | `FileCheck2` | 18px | 22px | 1.8 | Permit records and checks |
| Authority Cases | `Landmark` | 18px | 22px | 1.8 | External authority context |
| Issues | `TriangleAlert` | 18px | 22px | 1.8 | Exception and risk attention |
| Notifications | `Bell` | 18px | 22px | 1.8 | Notification stream |
| Administration | `Settings` | 18px | 22px | 1.8 | Configuration and ownership |
| Operating Guide | `BookOpen` | 18px | 22px | 1.8 | Product guidance and definitions |

## Supporting icons

The same `Icon` wrapper supplies `FileSignature` for contract surfaces, `PackageCheck` for handover surfaces, `ShieldCheck` for controlled/provenance states, `CircleAlert` for blockers, `CircleCheck` for confirmed states, and `ArrowUpRight` / `ArrowLeft` / `Plus` / `X` / `Search` / `HelpCircle` for actions and controls.

All icon instances inherit `currentColor`, use the shared wrapper, and render with a consistent Lucide outline treatment.

