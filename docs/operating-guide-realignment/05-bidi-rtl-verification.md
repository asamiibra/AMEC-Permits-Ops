# Bidi / RTL Verification

- Guide root switches between `lang="en" dir="ltr"` and `lang="ar-EG" dir="rtl"`.
- The language control is a semantic button group with `aria-pressed` state.
- The Guide keeps the current route while switching language and persists the Guide-only preference.
- Mixed Latin terms are isolated with `bdi dir="ltr"`.
- The responsive Guide has no horizontal overflow at 390px in English or Arabic.
- Application pages remain English/LTR; the Guide remains the intentionally bilingual surface.
