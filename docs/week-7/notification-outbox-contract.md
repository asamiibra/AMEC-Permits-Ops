# Notification Outbox Contract

`NotificationEvent` is the durable outbox record linking a finding and workflow task to a recipient, role, channel, event type, subject, body preview, attempt/delivery timestamps, failure code, external reference, and correlation ID.

Statuses are `PENDING`, `DELIVERED`, `FAILED`, and `SUPPRESSED`. Retry updates the failed event and audits `NOTIFICATION_RETRIED`; it does not create a duplicate task. Raw sensitive content is not copied into the body preview.
