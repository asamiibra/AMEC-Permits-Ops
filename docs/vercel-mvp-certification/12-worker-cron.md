# Workers and cron

No `crons` entry exists in either Vercel project configuration. No Vercel worker trigger is deployed. The current MVP is therefore read/API certified only; outbox draining, recovery scheduling, overlap handling, duplicate delivery, and cron authentication are deferred rather than claimed.

If a worker is added, it must invoke an ordinary authenticated endpoint and remain idempotent against PostgreSQL outbox state. Vercel timing and duplicate-delivery constraints are documented in [Cron usage and pricing](https://vercel.com/docs/cron-jobs/usage-and-pricing).
