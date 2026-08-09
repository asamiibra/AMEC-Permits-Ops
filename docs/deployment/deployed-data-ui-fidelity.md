# Deployed data and UI fidelity

Verification date: 2026-08-09 UTC. Browser checks used the deployed frontend with no API interception or mock substitution.

## API fidelity

Direct backend and frontend proxy responses were compared for `/api/projects`, `/api/applications`, `/api/dashboard`, `/api/findings`, `/api/tasks`, `/api/notifications`, and `/mock-authority/applications`. Every comparison returned HTTP 200 JSON and equivalent payloads. Counts were 4 projects, 4 applications, 0 findings, 0 tasks, 0 notifications, and 4 mock-authority applications.

The dashboard returned active projects 3, returned applications 1, open RAID items 10, pending decisions 6, and inquiries not asked 7. The findings and task endpoints returned the canonical fixture metadata even when their row counts were zero; no synthetic findings or notifications were invented to make an empty state look populated.

## Screen checks

| Screen | Route | Observed fixture evidence | Result |
|---|---|---|---|
| My Work | `/work` | “Resume permit work” and `GHCE-2026-0142` / Al Noor Villa | PASS |
| Permits | `/permits` | Four canonical projects, including Al Noor Villa | PASS |
| Issues | `/issues` | Open findings 0, blocking findings 0, blocked packages 4, permits in scope 4 | PASS |
| Notifications | `/notifications` | Unread/visible 0, failed delivery 0, failure rate 0% | PASS |
| Project & Sources | workspace route | Al Noor Villa / canonical project visible | PASS |
| Verify Data | `/verify-data` | “Verify the facts that drive the permit” | PASS |
| Prepare Package | `/prepare-package` | “Prepare Package” | PASS |
| Municipality Preparation | `/municipality-preparation` | “Municipality Preparation” | PASS |
| Final Review | `/final-review` | “Final Review” | PASS |
| Authority Review | `/authority-review` | “Authority” | PASS |
| History | `/history` | “History” | PASS |
| About | `/about` | “PermitOps helps AMEC” | PASS |
| Inputs & Go-Live | `/work` drawer | Visible info dialog opened from the `Inputs & Go-Live` control | PASS |

All listed routes returned HTTP 200, completed their API calls without 4xx/5xx failures, and showed no application error banner. A full reload of `/permits` retained the canonical project. A fresh browser context opened `/work` with the same fixture data.

The verified tenant/office is synthetic AMEC / QEC-DOHA. The demonstrated role is the existing Permit Preparer role; no authorization boundary was bypassed. Arabic content remains limited to the existing operating-guide surface and was not added to general UI screens.

## Durability

Five separate direct backend requests to `/api/projects` returned the same four canonical project numbers. The reload and new-session browser checks also returned the same fixture project. This demonstrates durable Neon-backed data across serverless requests and browser contexts.
