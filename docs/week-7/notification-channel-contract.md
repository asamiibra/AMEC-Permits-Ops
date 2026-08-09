# Notification Channel Contract

The bounded channel abstraction supports `IN_APP`, `MOCK_EMAIL`, and `MOCK_TEAMS` for Week 7. Future `EMAIL` and `TEAMS` adapters are explicit seams and are not configured with real credentials.

In-app delivery succeeds in the synthetic path. Mock external channels can succeed or be deliberately forced to fail. Failure is represented on `NotificationEvent` and never changes the finding/task to closed.
