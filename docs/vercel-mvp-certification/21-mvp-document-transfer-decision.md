# MVP document-transfer decision

Keep ordinary small synthetic/document requests on the API path only within the measured Vercel body limit. Do not send the 17 MB FORME archive through a Vercel Function. The current MVP uses PostgreSQL-backed synthetic Master Content bytes for demo reads/downloads and blocks filesystem SOR writes.

The later real-document path is a portable direct-to-authorized durable store flow with size/content authorization, hash/read-back verification, and an application transaction that decides publication. Object existence alone must not publish a DocumentVersion.
