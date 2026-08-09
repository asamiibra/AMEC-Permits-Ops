# PermitOps language-toggle persistence fix report

Status: PASS

## Root cause

The global locale provider persisted `permitops-locale` and updated document direction, but its DOM localizer translated text and attributes in place without retaining a reversible English source. A return to English could therefore leave Arabic text or attributes behind. `AboutPermitOpsPage`, `ReadinessDrawer`, and `Week7` also carried independent language state, allowing a page-level value to diverge from the global provider.

The detailed finding is recorded in [language-toggle-root-cause.md](language-toggle-root-cause.md).

## Corrective implementation

- Added the single application locale type `AppLocale = "en" | "ar-EG"`.
- Added the canonical persistence key `permitops.locale`.
- Normalized `en`, `en-US`, `english`, `ar`, `ar-EG`, and `arabic`; unknown values fall back to English.
- Migrated known legacy keys once, wrote the canonical key, and removed the legacy keys.
- Made DOM localization reversible so English restores the original English text and attributes.
- Derived `lang`, `dir`, body direction, root direction, and RTL shell placement from the global locale.
- Removed duplicate mutable language state from About, the readiness drawer, and Week 7; the readiness drawer keeps only a derived content label for its existing bilingual copy map.
- Preserved route, permit stage, drawer state, role, and business data while toggling.
- No backend source files were changed.

## Verification

| Check | Result |
|---|---:|
| Backend regression (`make test`) | PASS — 72 passed |
| Frontend unit/component tests | PASS — 23 passed in 8 files |
| Focused locale tests | PASS — 7 passed |
| Frontend typecheck (`npx tsc -b --pretty false`) | PASS |
| Frontend production build | PASS |
| Mocked browser regression (`browser-e2e`) | PASS — 112 passed |
| PostgreSQL-backed real-stack browser suite | PASS — 6 passed |
| Edge real-stack browser suite | PASS — 6 passed |
| Golden Path v1 | PASS |
| Golden Path v2 | PASS |
| Acceptance rehearsal | PASS |
| Canonical fixture check | PASS |
| `git diff --check` | PASS |

The PostgreSQL browser checks used a temporary clone of the existing seeded synthetic `permitops_test` database and removed that clone after verification. No repository database was deleted, replaced, or regenerated.

The first Edge invocation without a backend produced three environment-only failures because `127.0.0.1:8000` was unavailable. The rerun with the seeded PostgreSQL backend passed all six tests. A fresh SQLite seed similarly exposed the existing owner-rehearsal assumption that an approved package already exists; this was not a locale failure and was resolved for verification by using the repository's seeded PostgreSQL test fixture, without changing application code.

## Evidence

- [language-toggle-result.json](../../artifacts/bugfixes/language-toggle-result.json)
- [English notifications baseline](../../artifacts/bugfixes/language-toggle-notifications-en-before.png)
- [Arabic notifications state](../../artifacts/bugfixes/language-toggle-notifications-ar-after.png)
- [English restored state](../../artifacts/bugfixes/language-toggle-notifications-en-restored.png)

All required synthetic fixtures and existing evidence artifacts remain in place. No local-only generated state is included by the fix.
