# Regulatory Reuse Design

The Completion AuthorityCase reuses RegulatoryJourney, AuthorityCase, AuthorityCaseSubject, RegulatoryRelation, RequirementPolicyVersion, RequirementInstance, CaseEvidenceSelection, PhysicalEvidenceItem, FormInstance, PreparationRevision, SubmissionPackage, SubmissionPrecheckRun, SubmissionAttempt, ExternalSubmissionSnapshot, AuthoritySubmissionCycle, AuthorityCaseFinding, and AuthorityOutcome.

The existing generic Preparation/Submission loop remains the only preparation engine. Submission authorization creates pending external confirmation; it does not claim external submission. Manual confirmation creates the canonical external snapshot and immutable cycle. Findings use AuthorityCaseFinding; resubmission creates new P2/SP2/C2 records while C1 remains immutable. Verified Completion uses AuthorityOutcome with exact cycle, reference, issuing body, date, and artifact.
