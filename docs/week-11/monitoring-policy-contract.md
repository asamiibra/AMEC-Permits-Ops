# Monitoring policy contract

`MonitoringPolicy` pins scenario/application, environment, evidence class, allowed read operations, adapter/version, read-contract version, fallback mode, failure budget, and lifecycle status. `SYNTHETIC_ACTIVE` is the seeded development mode. `PRODUCTION_APPROVED` is not seeded and cannot be reached by the synthetic enable endpoint. Cadence is represented as configuration (`MANUAL_DUE_RUN`), not a hardcoded production promise.
