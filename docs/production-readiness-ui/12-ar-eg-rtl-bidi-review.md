# ar-EG, RTL, and BiDi review

The production-readiness drawer is intentionally English-only and fixed to `lang="en"`, `dir="ltr"`. Arabic/RTL is preserved only in the Operating Guide; the drawer has no language toggle and no Arabic resource map.

The mobile layout keeps the trigger visible as an icon with its accessible name and presents the drawer as a full-height sheet. Browser tests cover opening the drawer, switching to Arabic, checking RTL direction, and confirming an isolated Latin token.
