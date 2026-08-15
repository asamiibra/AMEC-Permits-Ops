# Serverless lifecycle

The application initializes the SQLAlchemy engine at import and runs schema initialization only during application lifespan, not per request. Production health after deployment, repeated warm requests, and post-deployment browser/API acceptance all succeeded.

The runtime safety patch removes local synthetic SOR writes from Vercel paths. Cross-request response hashes for 32 concurrent reads were identical, with zero cross-request leakage. The remaining lifecycle limitation is that a direct process-kill experiment is not available through the public Vercel API; redeployment and fresh health startup provide the deployment recovery evidence.
