# Owner protection primitive

Tests cover previous AI bytes + current Owner bytes + new text mutations. An unrelated duration update preserves the Owner's paragraph; a conflicting proposed edit returns NEEDS_OWNER_REVIEW and retains current Owner text. Owner formatting changes also count as protected changes. Changed paragraph topology fails closed.

No browser save, database revision, crash/restart persistence, provenance workflow or general rich-text merge was implemented. End-to-end Owner preservation remains NOT_RUN.
