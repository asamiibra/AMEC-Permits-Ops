# External agreement guard

`ExternalAgreement` is not a current canonical entity. Billing uses the canonical typed `Contract.agreement_type` / `ContractRevision.agreement_type`, not filenames, folders, or free-text titles. The default eligible set is `AMEC_PROFESSIONAL_SERVICES` and `AMEC_SERVICE_CONTRACT`; a typed external construction agreement is rejected with `CONTRACT_NOT_ELIGIBLE_FOR_AMEC_BILLING`. The negative Billing E2E creates an external typed contract and verifies no BillingPlan is created.
