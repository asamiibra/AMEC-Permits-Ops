# Language Toggle Root Cause

Date: 2026-08-08

## Finding

The reported `EN → AR → EN` defect was caused by competing locale ownership and a one-way DOM translation side effect.

Before this fix, `frontend/src/i18n.tsx` held a global `Locale` state of `"en" | "ar"` and persisted it as `permitops-locale`. The provider correctly wrote `document.documentElement.lang` and `document.documentElement.dir`, but `localizeDom()` translated existing text nodes and attributes in place. It had no restoration path for the original English values. When React did not recreate a translated node, Arabic text and attributes could remain after the locale changed back to English.

## Competing state and storage

- `LocaleProvider` owned the global `en | ar` state and `permitops-locale`.
- `AboutPermitOpsPage` independently read and wrote `permitops-about-language` and held `localLang`. This could briefly reapply Arabic when the page mounted.
- `ReadinessDrawer` held a second `lang` state and synchronized it through an effect. It was a duplicate mutable representation of the application locale.
- `FindingsConsolePage` held an independent `rtl` boolean and exposed a page-local layout toggle.
- `permitops-role` in `sessionStorage` is unrelated role state and was preserved.

The locale-related keys found in the frontend were `permitops-locale` and `permitops-about-language`. The fix uses only `localStorage["permitops.locale"]`. Known legacy keys are read once for migration, normalized, written to the canonical key, and removed so they cannot reapply stale Arabic.

## Why Arabic activated but English did not fully reset

Arabic activation changed the provider state, set the document to `ar-EG`/`rtl`, applied the Arabic body class, and mutated matching English DOM text into Arabic. On the return transition, the document attributes were changed back, but the mutated text and attributes had no corresponding reverse operation. Page-local state and the About legacy key added separate opportunities for Arabic to survive or reappear. The result was a mixed state: document direction could be English/LTR while visible copy or page layout still reflected Arabic/RTL.

## Corrective design

- The authoritative application state is now `AppLocale = "en" | "ar-EG"` in `LocaleProvider`.
- The canonical persistence key is `permitops.locale`.
- Legacy values are normalized as `ar`/`arabic → ar-EG`, `en-US`/`english → en`, and unknown values → `en`.
- Direction is derived only from locale: `ar-EG → rtl`; `en → ltr`.
- The document, body, application root, and known locale classes are synchronized on every change.
- DOM localization tracks original text and attributes and restores them when English is selected.
- About, Inputs & Go-Live, and Findings now read and change the shared provider state; none owns application language independently.
- The shell explicitly returns to LTR row order, while RTL uses the mirrored row order. AMEC logo assets remain untransformed.
