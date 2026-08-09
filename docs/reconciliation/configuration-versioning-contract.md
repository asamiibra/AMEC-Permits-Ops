# Configuration Versioning Contract

Consequential configuration is represented by immutable `ConfigurationArtifact` records and deterministic `ConfigurationBundle` records. Each artifact exposes `stable_id`, `version`, `checksum`, `effective_from`, `effective_to`, `status`, `source_basis`, and semantic payload. A bundle exposes its ordered artifact identities, bundle version, checksum, effective window and status.

The bundle covers scenario, requirement configuration, field authority, target rendering, attachment taxonomy, municipality controls and FindingCode taxonomy. A semantic change creates a new artifact/bundle identity and a `MaterialChangeEvent`; an old version is never edited in place.

Consequential records retain `configuration_bundle_id` where applicable: readiness evaluation, package, rendered form, Excel projection, PreparationRevision, PortalIntendedState and AuthorityPrecheckRun. Findings retain FindingCode version/checksum. The current bundle is never used to reinterpret a historical record.

