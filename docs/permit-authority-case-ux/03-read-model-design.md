# Read-model design

## Portfolio projection

`GET /api/permit-ux/portfolio` returns a paginated projection. It accepts `q`, `lane`, `stage`, `system_status`, `external_body_id`, `service_type_id`, `has_blockers`, `has_open_comments`, `page`, and `page_size`. The server filters before pagination and omits blobs, snapshot payloads, and sensitive source text.

Each row contains:

- project name and project reference;
- authority case reference and the approved authority identifier, or `Pending`;
- derived stage: Setup, Requirements, Preparing, Precheck, Ready to Submit, Pending External Confirmation, Submitted, Response Required, Resubmission, Decision Received, or Closed;
- derived system status: On Track, Needs Action, Blocked, Waiting External, Stale, or Closed;
- derived blocker summary and open-finding count;
- external body, service, and safe date display state;
- stable case id and deep-link target.

Stage and system status are projections, not persisted universal statuses. The projection is assembled in bulk to avoid one query per case and is permission-filtered by project/case visibility before response.

## Case workspace projection

`GET /api/permit-ux/cases/{case_id}` returns a composed workspace with `overview`, `project_details`, `requirements`, `documents`, `drawings`, `forms`, `comments`, `submission_history`, `permit_license`, and `history`. Each section includes source identifiers and provenance where useful. Missing canonical data is represented as an empty state with an explanation.

## New-case context

`GET /api/permit-ux/new/context` returns activated projects, active authority catalogs, accepted-scope suggestions, and prior-case context. `POST /api/authority-cases` remains the canonical case-creation command. The UX sends an idempotency key and never creates a proposal-only case.

## Derived-state rules

1. Outcome takes precedence and yields Decision Received or Closed.
2. Open authority findings yield Response Required; a subsequent cycle is Resubmission.
3. An external submission attempt awaiting confirmation yields Pending External Confirmation.
4. A confirmed/under-review cycle yields Submitted and the Authority Review lane.
5. A failed precheck yields Precheck and Blocked.
6. Existing preparation/evidence work yields Preparing or Ready to Submit.
7. Requirement instances without preparation yield Requirements; otherwise Setup.

Blockers come from required requirement state, evidence validity/selection, physical gate, baseline validity, precheck checks, and open blocking findings. Open Comments is the count of open `AuthorityCaseFinding` records.
