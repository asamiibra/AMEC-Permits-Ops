# Role boundaries

The shell continues to use `SYSTEM_ADMIN` / `OWNER_SPONSOR`, `COMMERCIAL_APPROVER`, and `RESPONSIBLE_ENGINEER` demo roles while API requests continue to receive the existing role header.

System Admin is exposed only to Owner/Admin roles. Finance is exposed to Owner/Admin and Business Development. Engineering retains technical delivery access without the system Admin or Finance navigation item. This is navigation visibility; backend authorization remains the enforcement boundary.
