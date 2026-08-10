# Engineering Works E2E

Engineering Works use canonical `E-xxxx` identity and verified current versions. A material v2 change preserves v1, marks an explicit EngineeringReview dependency `NEEDS_REVALIDATION`, creates one Finding/Issue, one AMEC Work task, and role-scoped notification deliveries. Normal upload noise is suppressed by the materiality/propagation contract and event-delivery uniqueness.

Dedicated Permit and generated Reports consumer UIs are absent; the binding, eligibility, dependency, and lineage seams are proven and classified accordingly.

Results: `ENGINEERING_WORK_CREATE_E2E_PASS`, `ENGINEERING_WORK_ELIGIBILITY_E2E_PASS`, `ENGINEERING_REVIEW_MASTER_SOURCE_E2E_PASS`, `ENGINEERING_REVALIDATION_E2E_PASS`, `ENGINEERING_ISSUE_PROJECTION_E2E_PASS`, `ENGINEERING_WORKFLOW_TASK_E2E_PASS`, `ENGINEERING_NOTIFICATION_E2E_PASS`, `NORMAL_ENGINEERING_UPLOAD_SPURIOUS_ISSUE_ZERO`, `NORMAL_ENGINEERING_UPLOAD_SPURIOUS_WORK_ZERO`, `DUPLICATE_ISSUE_CREATION_ZERO`, `DUPLICATE_WORK_CREATION_ZERO`, `DUPLICATE_NOTIFICATION_CREATION_ZERO`.
