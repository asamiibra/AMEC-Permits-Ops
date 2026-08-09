# Localization boundary: Operating Guide only

PermitOps operational screens are intentionally English-only and fixed to `lang="en"` / `dir="ltr"`. This includes the shell, My Work, permit workflows, readiness, findings, lineage, attachment/grid controls, administration, and expansion screens.

Only `/about` (also reachable as `/how-permitops-works`) is bilingual. Its `AboutPermitOpsPage` owns a local `GuideLocale` state and persists it under `permitops.operatingGuide.locale`. Arabic copy, RTL layout, BiDi isolation, and the `English` / `العربي` controls are scoped to the guide root; toggling the guide never changes the document or operational shell.

The former global locale provider and `permitops.locale` state are removed. The application ignores and clears stale global locale keys so an old Arabic preference cannot reapply to operational UI. Arabic source/business data and backend Arabic normalization/OCR/extraction behavior remain unchanged.

Verification is covered by the frontend unit boundary tests and `frontend/browser-e2e/language-toggle.spec.ts`: stale global state is cleared, operational routes stay English/LTR, the guide persists Arabic locally, and Inputs & Go-Live remains English/LTR.
