# Regulatory Core

Implemented canonical entities and APIs for ExternalBody, ExternalBodyUnit, Jurisdiction, ServiceType and effective-dated ServiceTypeVersion, RegulatoryLifecyclePhase, RegulatoryJourney, AuthorityCase, Subject fields, late AuthorityCaseIdentifier, AuthorityCaseWorkPeriod, ExternalInteractionProfile, AuthorityOutcome, and RegulatoryRelation.

Case creation is explicit and separate from Proposal intake. Mutable catalog records are protected by owner RBAC and active versions are immutable; audit events are recorded for writes.
