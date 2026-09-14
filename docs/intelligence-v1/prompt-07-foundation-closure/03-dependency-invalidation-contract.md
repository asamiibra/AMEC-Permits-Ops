# Dependency and invalidation contract

`intelligence_foundation.py` captures exact dependency type/id/hash edges, revalidates canonical currentness, selectively invalidates causally bound products, preserves prior products, and deduplicates repeated source events. Lineage is materialized in `AIWorkProductDependency` and summarized by `lineage_hash`.
