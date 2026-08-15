# Upload payload

The deployed platform accepted a 1,024-byte request and a 4,300,000-byte request through the Proposal intake route far enough to return FastAPI validation (`422`). A 4,700,000-byte request was rejected by Vercel with `413 FUNCTION_PAYLOAD_TOO_LARGE`. Current documented limit: 4.5 MB; see [Vercel upload guidance](https://vercel.com/kb/guide/how-to-bypass-vercel-body-size-limit-serverless-functions).

`/Users/ahmedsami/Downloads/FORME.zip` is 17,009,370 bytes, so it cannot be sent through the current request-body path. The current MVP does not expose a deployed archive intake endpoint. A future direct-to-object-storage transport must keep upload authorization, integrity verification, and business publication separate.
