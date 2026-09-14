# Stage capability contract

proposal_projection now exposes action_capabilities keyed by the P04C action vocabulary. Each entry contains available, required capability, and a server reason when unavailable. Stage checks and role capability checks are computed server-side; UI role sets remain only backward-compatible test fallbacks.

The Contract handoff preview returns server gate objects. The Proposal handoff endpoint remains an eligibility record and does not create a Contract or activate a Project.
