# Drawing metadata controls v0

The synthetic controls compare drawing metadata against current verified canonical facts. Controls are blocking when stated below and produce `PASS`, `FAIL`, or `NEEDS_REVIEW`.

| Control | Drawing metadata | Canonical comparison | Blocking |
|---|---|---|---|
| `DRAWING_PLOT_MATCH` | PLOT | `PROPERTY.PLOT_NUMBER` | Yes |
| `DRAWING_ZONE_MATCH` | ZONE | `PROPERTY.ZONE` | Yes |
| `DRAWING_OWNER_MATCH` | OWNER_EN | `OWNER.NAME_EN` | Yes |
| `DRAWING_REVISION_PRESENT` | REVISION | Version metadata | Yes |
| `DRAWING_PROJECT_MATCH` | PROJECT | Canonical project number | Yes |

No drawing revision is auto-selected as authoritative. A fail stays visible for human review.
