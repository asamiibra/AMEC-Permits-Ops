# RBAC and isolation

The implementation retains visible global roles Owner, Business Development, and Engineering. Category assignment capability is present for System Admin, Owner, and Engineering, and absent for Business Development. All Drawing Review, rendition, comment, AI, assignment, and finding-link routes validate project scope; AuthorityCaseFinding links additionally validate the case subject project.
