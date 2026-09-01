# Governance-gap closure

- Archived `DefinitionEntry` rows are excluded from governed retrieval.
- `MasterContentItem.needs_review` rows are excluded from authoritative
  retrieval and consumer resolution.
- Restricted reference samples remain owner-visible as explicitly
  `RESTRICTED_REFERENCE` evidence but are excluded from non-owner context and
  cannot become an authoritative answer or prefill source.
- Retrieval purposes are capability-bound: `FORM_PREPARATION` is limited to
  Owner/System Admin/Permit Preparer; proposal and contract preparation have
  corresponding current role gates; unsupported purposes fail closed.
- Consumer use additionally requires active binding, active/current item,
  reviewed current DocumentVersion, source reference, governance readiness,
  and exact item/version identity.
