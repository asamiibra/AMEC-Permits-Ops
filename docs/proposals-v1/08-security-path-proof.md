# Source path negatives

Focused tests reject traversal, absolute paths, alternate streams, backslashes, repeated separators, excluded projects, symlink files/directories and FIFOs. Unicode and shell characters stay literal filenames; no shell is used by the connector. Reads enforce file and inventory limits. ZIP/RAR source contents are not extracted.

Package mutator separately rejects duplicate/traversing ZIP entries, missing relationships, DTD/entity XML, unsupported UTF-16 byte-offset input, stale anchors and overlapping edits.

Endpoint RBAC and cross-project HTTP access are NOT_RUN because routes are not implemented. These path tests must not be promoted to endpoint security certification.
