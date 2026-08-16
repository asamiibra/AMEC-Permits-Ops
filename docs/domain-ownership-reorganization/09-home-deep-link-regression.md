# Home, AMEC Work, Issue, and Notification deep links

Home continues to consolidate attention, Finance, content, and activity while keeping Finance out of the primary sidebar. Its Stage 2 card now points to `/contract-mobilization`; its Finance panel still points to `/billing`.

Home, AMEC Work, Issue, and Notification presentation links pass backend-provided URLs through a small compatibility normalizer. Legacy `/admin/contracts`, `/admin/project-activation`, and `/admin/invoices` targets are converted to their owning workspace while preserving IDs, query parameters, and issue/notification return context. Underlying work, issue, notification, read state, and audit identity are unchanged.

HOME_ACTION_LINK_RECONCILIATION_PASS=1
