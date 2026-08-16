# Visual specification

The icon system is intentionally small and repeatable:

| Property | Final value |
| --- | --- |
| Primary family | Lucide React |
| Navigation SVG size | 18 × 18px |
| Navigation slot | 22 × 22px, fixed flex basis |
| Navigation label gap | 12px |
| Default stroke width | 1.8 |
| Color model | `currentColor` from the surrounding semantic state |
| Alignment | centered inside the fixed slot; SVG `display: block` |
| Focus treatment | existing visible focus ring preserved on controls |
| Source of truth | `frontend/src/Icon.tsx` |

The fixed slot prevents label jitter across icon shapes. The shared wrapper sets `focusable="false"` and makes unlabeled icons `aria-hidden`; icon-only controls retain their existing accessible labels.

