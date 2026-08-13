# Pre-activation billing context

Project activation policy is read from the canonical runtime decision `BILLING_PROJECT_REQUIREMENT_POLICY`, defaulting safely to `REQUIRED`. Under REQUIRED, an unactivated project produces `NEEDS_PROJECT_ACTIVATION`. Under an Owner-configured optional policy, the DTO can return `project_id: null`, `project_code: null`, explicit `NOT_ACTIVATED`, and a non-canonical Contract/Proposal project context snapshot without fabricating a Project. Activation later changes only the live read model; historical Contract/Preparation snapshots remain pinned.
