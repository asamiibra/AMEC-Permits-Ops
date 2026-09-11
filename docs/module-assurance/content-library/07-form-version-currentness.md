# Form Version and Currentness

For reusable Content Library Forms, eligibility requires an active item, active binding, current item pointer, reviewed `DocumentVersion`, current master status, and a non-pending source reference. Frozen AMEC-owned proposal/contract purposes still require the canonical AMEC-owned governance profile.

Official authority form currentness remains owned by Source18/current regulatory controls. `POST /api/source18/official-form-versions` records official-form metadata on the controlled `DocumentVersion` and supersedes prior current metadata. Packet manifest and submission controls require the exact current OfficialFormVersion and fail closed for unknown/stale state.

This is intentionally a seam, not a duplicate Content Library OfficialFormVersion authority. The typed ownership decision is recorded in `20-open-product-decisions.md`.
