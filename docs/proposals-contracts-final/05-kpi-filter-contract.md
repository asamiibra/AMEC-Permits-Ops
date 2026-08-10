# KPI and filter contract

The six KPI predicates are registered once in `backend/app/services/backend_realignment.py::KPI_PREDICATES`. Summary counts, canonical list filters, and the legacy register KPI payload derive from that registry. The frontend consumes backend counts and predicate-backed rows.

An error response is rendered as an error/retry state, never as an empty or zero-count register.
