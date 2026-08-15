# archive security

The reader never extracts archive members to disk. It rejects absolute, UNC, drive-qualified and traversal paths; NULs; duplicate normalized paths; case-fold collisions; encrypted entries; symlink entries; nested archives; excessive entries/files/bytes; oversized members; and suspicious compression ratios. It streams a single member through a bounded read and verifies the declared size and fresh SHA-256.

Focused archive tests passed for Arabic and spaces, empty folders, unsafe paths, case collisions, nested archives and entry limits. A malicious archive is rejected before intake promotion and produces no partial managed publication.
