# Monitoring retry policy

Transient network, portal-unavailable, and rate-limit failures are the only safe retry classes. Contract drift, identity mismatch, parse failure, auth/MFA requirements are not treated as transient. Failure count is bounded by policy and the policy pauses when its configured budget is reached.
