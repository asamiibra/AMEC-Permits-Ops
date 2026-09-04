# Material change and revalidation

Master version promotion already records `MasterContentChangeEvent` and propagates configured `MasterContentDependency` changes. Existing dependency status/task/finding behavior remains the governed open-work path; closed historical work is not repinned.

For BD Proposal, the accepted snapshot now records a master-content fingerprint covering the exact template/checklist resolutions. A later canonical version or resolution change is visible as `master_content_changed` and requires an explicit Proposal revision before acceptance. Creating that revision and accepting it is a human/domain action; no automatic replacement or reissue occurs.

Non-master Proposal field changes remain distinct from master-source revalidation. Renderer and form runtime source drift remains fail-closed through `NEEDS_REVALIDATION`.
