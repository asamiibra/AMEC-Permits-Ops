# Environment disclosure system

The global shell remains the persistent source of truth. The final UI visibly discloses:

- `SYNTHETIC PROTOTYPE`;
- `Test data only`;
- `Simulated integrations`.

Repeated compact page badges are visually suppressed where the global shell already communicates the same fact. The underlying DOM remains truthful through the global shell, and page-specific warnings remain available only when the page needs special context. Representative final screens all report `environmentVisible: true` and `compactDisclosureHidden: true` in `visual-qa.json`.
