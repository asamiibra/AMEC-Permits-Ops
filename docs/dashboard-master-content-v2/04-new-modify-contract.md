# New / Modify Contract

New creates one canonical `MasterContentItem`, one `DocumentVersion`, one SOR artifact, an immutable audit/event trail, and optional module bindings. Modify creates a new immutable version. Metadata-only changes reread the current source and create a `METADATA` version rather than mutating history. See `new-modify-result.json`.
