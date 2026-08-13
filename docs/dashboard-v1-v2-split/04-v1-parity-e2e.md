# V1 Parity E2E

The focused Vitest contract in `frontend/tests/dashboard-v1-v2-split.test.tsx` verifies that V1 renders the legacy heading and canonical form item, omits `Advanced governance filters` and `Content ownership`, and retains the standalone Version column/value.

The real-stack browser test verifies `/dashboard` renders the four library headings and contains no advanced governance filter disclosure. Existing Dashboard owner/browser coverage and the full backend suite remain green, preserving New/Edit/History and shared canonical CRUD regression coverage.

Result: V1 legacy presentation checks passed with zero focused failures.
