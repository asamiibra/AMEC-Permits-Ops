# Role and access matrix

Owner (`SYSTEM_ADMIN`) can create, version, bind, revise, and archive master content. Business Development (`COMMERCIAL_APPROVER`) and Engineering (`RESPONSIBLE_ENGINEER`) can read applicable content but direct master writes, binding changes, and protected Administration access return 403. The combined gate is enforced by capability plus Used In/module applicability.

Evidence: `backend/tests/test_dashboard_master_content_v2.py`, `backend/tests/test_owner_dashboard_master_content.py`, `frontend/browser-real-stack/admin-owner-ready.spec.ts`, `frontend/browser-real-stack/admin-forms-real-stack.spec.ts`, and `artifacts/dashboard-e2e/role-access-matrix.json`.

Results: `OWNER_MASTER_CONTENT_WRITE_PASS`, `BD_APPLICABLE_MASTER_READ_PASS`, `BD_MASTER_CONTENT_WRITE_DENIED_PASS`, `ENGINEERING_APPLICABLE_MASTER_READ_PASS`, `ENGINEERING_MASTER_CONTENT_WRITE_DENIED_PASS`, `DIRECT_API_UNAUTHORIZED_WRITE_ZERO`.
