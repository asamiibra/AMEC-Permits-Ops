# Interaction and regression coverage

The real-stack Playwright suite `frontend/browser-real-stack/admin-owner-ready.spec.ts` covers:

- all owner Administration cards and separate Inputs & Go-Live navigation;
- opening Notifications & Follow-up, saving 36 hours, and verifying the value after reload;
- opening Data & Connections, running a real backend connection test, and showing the result;
- opening Project & Folder Setup and verifying a backend-derived reference projection;
- hidden Administration navigation and denied direct paths for Business Development and Engineering;
- narrow viewport overflow.

Backend tests cover category reclassification, persona denial, safe connection fields, connection test behavior, bounded persistence, and audit history. Frontend TypeScript/Vite build is also part of the verification record.
