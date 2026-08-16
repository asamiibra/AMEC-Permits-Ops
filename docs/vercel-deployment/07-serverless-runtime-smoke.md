# Serverless runtime smoke

The bounded smoke exercises repeated warm requests, a fresh/cold-ish request, parallel read-only requests, and a reconnect-visible `/health` query. It does not rely on process memory, local filesystem persistence, SQLite, or `/tmp` for durable state. Background processing is not asserted by this frontend-only release; any absent Vercel cron/outbox trigger remains deferred.
