# Stale replay proof

Replay requires a successful ledger and a `CURRENT` work product. The foundation replay path also revalidates the snapshot and invalidates changed products before rejecting replay with `AI_STALE_WORK_PRODUCT_REPLAY`.
