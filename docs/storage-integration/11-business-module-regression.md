# Business-module regression boundary

Existing fixture flows remain green while the permanent service is introduced.
The remaining legacy fixture call sites are explicitly isolated behind
`storage.legacy.legacy_synthetic_adapter`; they fail closed when a real SMB
provider is selected. Module-by-module migration to `DocumentStorageService`
must complete before Owner production cutover.
