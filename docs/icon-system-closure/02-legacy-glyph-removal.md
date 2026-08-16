# Legacy glyph removal

The final source and browser audit contain no placeholder glyphs in primary navigation or action-icon positions. Existing prose arrows and the `PROPOSAL • CONTRACT • PERMIT` eyebrow are retained only as readable text separators/process notation; they are not rendered as controls or icon slots.

## Required counters

```text
UNICODE_NAV_ICON_COUNT=0
ASCII_ARROW_ICON_COUNT=0
EMOJI_ICON_COUNT=0
TEXT_GLYPH_AS_ICON_COUNT=0
MIXED_PRIMARY_ICON_FAMILY_COUNT=0
UNEXPLAINED_CUSTOM_SVG_ICON_COUNT=0
ICON_SIZE_INCONSISTENCY_COUNT=0
ICON_STROKE_INCONSISTENCY_COUNT=0
ICON_ALIGNMENT_DEFECT_COUNT=0
```

The wrapper contains no hand-authored SVG path data. Every normal icon is a Lucide component. Decorative textual arrows that occur inside explanatory sentences remain ordinary copy and do not substitute for a control icon.

