# Screen input/output matrix

Each registry row separates `runtimeInputs` from `runtimeOutputs` and from `customerRequirementIds`.

Runtime inputs are values or evidence the application reads during use: project identity, source documents, workflow state, findings, portal snapshots, permissions, and configured rules. Runtime outputs are things the screen produces or makes visible: verified facts, setup results, package manifests, handoffs, audit evidence, notifications, and reconciliation state. AMEC setup items are practical dependencies such as access, templates, roles, regulations, data locations, and test evidence.

The drawer caps display to 7 inputs and 6 outputs to remain compact while retaining the full registry in code and JSON artifacts.
