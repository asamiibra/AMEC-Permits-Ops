# Finding Deduplication Contract

Deduplication is deterministic and conservative:

1. stable external event ID;
2. exact payload/source-reference hash;
3. explicit normalized key;
4. otherwise preserve the event and mark `POSSIBLE_DUPLICATE_NEEDS_REVIEW`.

Deterministic duplicates create a linked `AuthorityEvent` and reuse the canonical finding/task. Uncertain duplicates are never fuzzy-merged; raw events remain inspectable and human resolution is required.
