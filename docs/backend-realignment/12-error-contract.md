# Error contract

Expected business failures use JSON detail envelopes with stable codes:
404 not-found, 403 `CAPABILITY_DENIED`, 409 identity/link/SOR conflicts, 422
readiness failures and 503 SOR unavailability. The global exception handler
still returns 500 only for unexpected failures with a correlation ID. Material
business endpoints do not convert exceptions into empty lists, empty maps or
zero counts.
