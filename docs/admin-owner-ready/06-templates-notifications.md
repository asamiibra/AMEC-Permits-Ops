# Templates & Notifications

`GET /api/admin/templates` combines the controlled Proposal/Contract template registry and Municipality form template registry into safe versioned projections. Synthetic stand-ins are labelled as such and prior versions remain visible where available.

`GET /api/admin/notifications` shows audiences, rule status, recent event count, and the current bounded setting. `PUT /api/admin/notifications/follow-up` accepts only 1–720 hours, persists the value in `ADMIN_RUNTIME_SETTINGS:AMEC`, and records `ADMIN_CONFIGURATION_UPDATED`. The UI retains a visible success/error result and the value survives refresh.
