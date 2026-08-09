# Configuration Lineage Validation

Validated lineage edges include:

`ConfigurationBundle → PackageReadinessEvaluation`, `ConfigurationBundle → Package`, `ConfigurationBundle → PreparationRevision`, `ConfigurationBundle → RenderedForm`, `ConfigurationBundle → PortalIntendedState`, `ConfigurationBundle → AuthorityPrecheckRun`, and `FindingCode(version/checksum) → Finding`.

Material TargetRenderingRule, FieldAuthorityRule, RequirementConfig or ScenarioConfig changes use the existing Week 8 traversal and create bounded stale/revalidation consequences. Document/fact changes continue through their existing document → observation → assertion → projection/package/revision/precheck graph. Configuration changes do not globally invalidate unrelated projects or evaluations when no lineage edge exists.

Historical bundle/artifact rows remain queryable. The old package/revision/precheck context is therefore reconstructable even after a replacement bundle is created.

