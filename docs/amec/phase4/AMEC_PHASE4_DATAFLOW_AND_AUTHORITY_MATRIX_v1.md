# Phase4 Dataflow and Authority Matrix

`SourceChangeEvent → Source Intake → DocumentEvidenceEnvelope → ClassificationEnvelope → ReviewDecision → VerifiedAssertion → ProjectionPlan → ProjectionReceipt → Work/Issue/Notification/Audit`

Each edge carries root event, source version, evidence IDs, rule IDs, Module Truth SHA, contract SHA, scope, capability, and correlation lineage.

The accepted Phase3C contract is authoritative; unresolved Owner decisions remain pending and protected actions remain human-only.
