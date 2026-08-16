# Icon system

## Final rule

`frontend/src/Icon.tsx` is the shared inline SVG family for navigation, status/support, empty-state, and control icons. It uses one outline language: `currentColor`, `1.8` stroke, round caps/joins, and a consistent `24 × 24` viewBox.

Targets:

- Sidebar: 16–18px.
- Toolbar/action icons: 14–16px.
- Support/status icons: 14–16px.
- Empty-state icon: restrained 40px container with a 16px family glyph.
- Icon/text gap: 6px through the shared button/link alignment rule.

The directional arrow keeps the existing visible `→` action-label contract while the surrounding navigation and support icon family is normalized. No emoji-style icons were introduced. Icon-only controls retain accessible labels or existing title/aria contracts.

## Rendered evidence

The final visual evidence records SVG icons on every representative route: Dashboard 13, Proposal Register 14, Completion 16, Engineering 14, Issues 21, and Admin 14. All evidence routes passed the serious/critical Axe gate.
