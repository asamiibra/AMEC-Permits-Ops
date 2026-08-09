# Portal contract revalidation

Re-enable requires a passing, reviewed `PortalContractValidationRun` for the same adapter/version. Revalidation changes the synthetic policy back to `SYNTHETIC_ACTIVE`; it never grants production authority. A validation without reviewer evidence cannot mark an adapter healthy.
