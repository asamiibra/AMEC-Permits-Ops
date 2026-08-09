# E6 handover control

Readiness is a deterministic configured checklist with `READY`, `BLOCKED`, or `NEEDS_REVIEW`. The handover form/output is rendered through shared templates. Human approval creates `HANDOVER_APPROVED_FOR_RELEASE`; explicit synthetic release evidence creates `HANDOVER_RELEASED`. Release is not project closure.
