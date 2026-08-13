# Performance and scale evidence

Portfolio status, catalogs, identifiers, and precheck checks are bulk-loaded before pagination; snapshot and binary blobs are omitted. The endpoint caps page size at 100. A 500-case synthetic load remains a follow-up benchmark before production deployment.
