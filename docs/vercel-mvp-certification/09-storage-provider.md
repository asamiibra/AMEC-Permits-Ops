# Storage provider

The final Vercel environment explicitly declares `STORAGE_PROVIDER=mock`. Health reports the provider as `mock-test` in synthetic TEST mode; real binary storage is not configured. Master Content download is durable in the synthetic mode because the deployed version bytes are retained in PostgreSQL, not in `/tmp` or the Vercel instance.

Real Owner/business documents are not authorized. Real Synology/SMB storage remains external and unverified. No silent provider fallback is permitted by the certified Vercel branch.
