# Browser acceptance

`frontend/browser-e2e/home-command-center.spec.ts` covers:

- Owner Home IA, seven stage targets, removed primary-nav labels, Finance/Content links, recent activity, notification bell, exact attention count/row parity, and serious/critical Axe violations.
- Responsive Home at 1920, 1440, 1280, and 1024 widths, with preserved legacy routes.
- Business Development and Engineering role-scoped navigation.

The dedicated Home suite passed 8 tests after the route-contract corrections. The supporting targeted regression suite passed 43/43 tests. The production build passed with only the existing large-chunk warning.
