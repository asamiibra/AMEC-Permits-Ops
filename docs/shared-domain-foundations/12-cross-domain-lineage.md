# Cross-Domain Lineage

The implementation supports these governed chains:

`MasterContentItem → DocumentVersion → SourceSection → RequirementPolicyVersion`

`MasterContentItem → DocumentVersion → SourceSection → TechnicalRuleSetVersion`

`MasterContentItem → DocumentVersion → FormAutomationProfile → FormInstance → GeneratedArtifact`

Requirement resolution accepts service type, jurisdiction, external body, and lifecycle context. Technical and form runtime records retain historical source/version references and refuse stale form sources.
