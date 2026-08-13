# Billing gate

The context returns `READY_FOR_BILLING_SETUP` only when the Contract revision is approved/finalized, core commercial fields exist, Project Activation exists, and payment terms/condition are human-verified. Otherwise it returns a deterministic blocker state.
