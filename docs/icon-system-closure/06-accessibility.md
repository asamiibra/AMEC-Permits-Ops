# Accessibility

The final icon wrapper uses `aria-hidden="true"` for decorative icons and supports an explicit label when an icon is meaningful by itself. Icon-only close, back, and add controls retain accessible names from their existing button or link labels. Text labels remain present beside navigation icons and action icons.

The browser audit checked all ten primary/deep routes plus three responsive Dashboard widths. Each screen had:

```text
consoleErrors=[]
seriousOrCritical=[]
horizontalOverflow=false
```

The dedicated browser run passed Axe serious/critical checks on every screen. Visible focus treatment and existing keyboard/action contracts were preserved; the existing UI closure suite also passed its focus and 200% zoom checks.

