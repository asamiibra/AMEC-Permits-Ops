# Event and persona contract

The backend owns visibility through `notification_visibility` and projects one event set for Owner, Business Development, and Engineering. Audience and domain rules are enforced server-side; the frontend only renders the returned projection.

Notification titles describe the event or change. Raw actor identifiers are sanitized at projection time.
