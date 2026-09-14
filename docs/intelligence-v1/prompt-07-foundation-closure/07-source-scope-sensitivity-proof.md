# Source scope and sensitivity proof

Document classifier proposals now require a server-loaded document version, exact current-version identity, and validated project scope. Classification and sensitive-data flags are derived from server metadata and field/document semantics; client requests cannot downgrade them. Raw source content is not persisted in the intelligence contracts.
