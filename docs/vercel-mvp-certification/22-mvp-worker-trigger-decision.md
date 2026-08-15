# MVP worker-trigger decision

No worker is required for the certified read-only synthetic MVP surface, so no Vercel cron is configured. Source-intake continuation, outbox draining, recovery leases, and retries remain deferred. AWS migration should provide the durable scheduler/worker trigger before those capabilities are enabled for real documents.
