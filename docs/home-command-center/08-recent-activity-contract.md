# Recent activity contract

Recent Business Activity uses the existing role-scoped `/api/work` `recent_changes` projection. It is bounded to five records, preserves the existing business event labels and timestamps, and creates no second audit or activity store. Empty or unavailable results remain explicitly empty/unavailable; Home does not synthesize activity.
