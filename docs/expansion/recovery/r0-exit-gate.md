# R0 recovery exit gate

The R0 exit gate is satisfied when the registry files, A15 links, Stage 2 dispositions, and prototype-only policy assertions pass together with the E2/E3/E4 endpoint rehearsal and original PermitOps regression.

Required labels:

- `A12_REGISTRY_RECONCILED`
- `A12B_REGISTRY_RECONCILED`
- `A15_REGISTRY_RECONCILED`
- `STAGE2_DISPOSITION_PRESERVED`
- `PROTOTYPE_DEV_BOUNDARY_ENFORCED`

This gate is an implementation and entry-rehearsal gate only. It does not authorize E5/E6 build activity, production use, live-pilot operation, external sends, accounting writes, or government submission.
