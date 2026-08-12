# RBAC

Owner/System Admin and Business Development can create, edit, manage sources, Accept, hand off, and manage go-live settings. Engineering can read the Proposal workspace but cannot create, edit commercial fields, or Accept. Dashboard master-content write remains owner/admin-only. These boundaries were checked by focused PostgreSQL tests, deployed API calls, and the browser Owner flow.

`FREEZE_PROPOSAL_RBAC_PASS` · `ENGINEERING_COMMERCIAL_WRITE_DENIED_PASS` · `BD_DASHBOARD_MASTER_WRITE_DENIED_PASS` · `UNAUTHORIZED_PROPOSAL_ACCEPT_ZERO`
