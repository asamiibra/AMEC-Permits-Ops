# ar-EG, RTL, and BiDi review

The drawer includes an English/Arabic toggle. Arabic content uses `lang="ar-EG"`, `dir="rtl"`, logical CSS properties, and `<bdi>`-style `LtrTerm` spans for IDs, route names, status codes, and other Latin tokens. The trigger retains an accessible Arabic name: `المدخلات ومتطلبات التشغيل`.

The mobile layout keeps the trigger visible as an icon with its accessible name and presents the drawer as a full-height sheet. Browser tests cover opening the drawer, switching to Arabic, checking RTL direction, and confirming an isolated Latin token.
