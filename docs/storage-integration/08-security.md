# Security boundary

Production must use a dedicated least-privilege SMB service identity, a
private route, an approved share/root, SMB2 or newer, explicit signing /
encryption policy, and a deployment secret reference. Secrets are not stored
in source, browser data, business rows or logs.

Filename and relative-path normalization rejects traversal, alternate share
injection, control characters, reserved Windows names, trailing-dot/space
ambiguity, Unicode normalization collisions and excessive path length.

ProposalOps authorization remains separate from SMB authorization. Legacy
human working roots are not immutable managed evidence.
