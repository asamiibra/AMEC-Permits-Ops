# Project Activation move

Project Activation remains an explicit section of the canonical Contract workbench, now reached from `/contract-mobilization/contracts/:id#activation`. The panel still requires the existing accepted Contract revision, Project Code, and Project Start Date, and posts to the existing audited activation endpoint.

The move does not make Contract creation activate a Project, does not alter idempotency, and does not create a second Project or activation record. The old `/admin/project-activation` compatibility route resolves to Contract & Mobilization; the old nested Admin Contract URL also resolves to the canonical business workspace.

Service Scope/ServiceEngagement remains a separate canonical concept. This run adds no flattening assumption between Contract, Project, and service scope.
