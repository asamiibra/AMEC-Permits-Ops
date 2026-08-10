# Canonical SOR promotion policy

Policy: `COPY_VERIFY_AND_ARCHIVE_SOURCE`. The synthetic adapter supports
configured copy/write plus metadata and hash verification; it does not claim a
production Synology move/archive API. Promotion is eligible only when the
canonical Project, root and exact folder template resolve and identity agrees.

Sources promoted are Tender Email, Tender Document, Tender Image, Client and
Proposal. The sequence is source hash verification → canonical target conflict
check → copy → target read-back → authoritative registration → historical
provisional state → lineage/audit. Same-hash retries reuse the canonical
record; different target hashes produce a typed `SOR_PROMOTION_CONFLICT`.
