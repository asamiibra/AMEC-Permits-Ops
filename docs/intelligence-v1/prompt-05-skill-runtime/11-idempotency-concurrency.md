# Idempotency and concurrency

Executed: identical completed requests replay the existing work product without provider execution; changed immutable identity returns `AI_IDEMPOTENCY_CONFLICT`; active reservations return `AI_REQUEST_IN_PROGRESS`; failed reservations require a new key. The unique ledger key plus reservation transaction closes the same-key race.
