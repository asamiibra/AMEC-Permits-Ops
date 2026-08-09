# Notification routing observability

Existing Week 7 notifications remain the durable event. Week 11 adds append-only `NotificationDeliveryAttempt` rows, exposes recipient/channel/failure/retry history, and reports delivery failure rate without sensitive comment labels. Failed delivery leaves the finding/task open.
