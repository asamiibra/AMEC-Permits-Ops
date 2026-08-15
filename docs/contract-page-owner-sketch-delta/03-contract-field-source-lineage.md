# Contract Field Source Lineage

The page labels each visible Contract fact with a source. Accepted Proposal values are read from the immutable accepted revision snapshot. Contract commercial edits create a new prospective `ContractRevision` with the prior revision preserved. Client party/contact values come from canonical ClientAccount and ClientContact records, with Proposal contact context used only as a controlled fallback. An Owner-entered Contract value is displayed as `Contract revision` and `diverged: true`; the upstream Proposal/Client source is not overwritten.

The PIN field intentionally has no guessed value. It displays `Not configured`, uses `OWNER_DEFINITION_REQUIRED`, and stays read-only until AMEC defines the semantic source. This is a safe unresolved state, not a silently invented identifier.
