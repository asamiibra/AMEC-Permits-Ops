# Pre-activation billing E2E

The runtime supports the two policy modes without globally deciding the Owner policy. In `PRE_ACTIVATION_ALLOWED`, ContractBillingContext can remain valid with `project_id = null`, and plan creation/activation can proceed by authorized human action; the snapshot remains present and no Project is created. In the default `PROJECT_REQUIRED` mode, context reports `NEEDS_PROJECT_ACTIVATION`. Issue has its own conservative policy and is not inferred from setup permission.

The current Owner Decision register does not contain a production-confirmed billing-policy choice, so no Owner decision was fabricated during certification. The implementation and negative gate are covered by source inspection and targeted billing behavior; production policy remains pending.
