# Portal Validation Finding Contract

`PortalValidationFindingRule` controls which persistent validation codes become durable findings. Configured examples include missing required attachment, required field missing, and wrong attachment category. Unconfigured/transient validation messages return `VALIDATION_CODE_IGNORED` and create no noise finding.

Configured findings retain preparation-revision linkage, raw validation text, source evidence, code, severity, owner, task, and notification.
