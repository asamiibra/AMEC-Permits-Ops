# AMEC Work final homepage audit

The homepage now presents one actionable cross-lifecycle queue for Proposal, Contract, Permit, and System work. The projection is backed by `backend/app/services/work_projection.py`; the UI is `frontend/src/AMECWork.tsx`.

The audit found and closed domain fallback to Permit, linked issue/task duplication, internal projection labels, generic CTAs, misleading filtered empty states, and Permit-first fixture bias. No deployment was performed.
