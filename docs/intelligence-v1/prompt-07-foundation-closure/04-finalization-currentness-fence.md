# Finalization currentness fence

`finalize_current_work_product` revalidates every snapshot dependency immediately before setting `CURRENT`. A changed dependency records `AI_CONTEXT_CHANGED_DURING_EXECUTION`, marks the output `STALE`, and leaves the provider response and citations queryable as history.
