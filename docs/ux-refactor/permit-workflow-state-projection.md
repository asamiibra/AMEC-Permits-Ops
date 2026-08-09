# Permit workflow state projection

`projectWorkflowStage()` in `frontend/src/WorkflowFirst.tsx` is a UI projection only. It reads application status and active findings; it does not create or mutate a second workflow state.

Rules include: RETURNED with an active finding projects to Comments & Corrections; UNDER_REVIEW/SUBMITTED projects to Authority Review; APPROVED/CLOSED projects to History / Close; preparation statuses project to Municipality Preparation; otherwise the permit starts at Project & Sources. A stage cannot be manually advanced from the UI.
