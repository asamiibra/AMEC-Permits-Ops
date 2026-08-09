# Prototype execution-authority contract

The recovery runtime is governed by one explicit policy:

`PROTOTYPE_DEV_ONLY` + `SYNTHETIC_IMPLEMENTATION_EVIDENCE`

The policy disables production enablement, real email, real accounting writes, real portal/government writes, production template release, professional-authority claims, and government submission. Communication records stop at `HUMAN_REVIEW` or `READY_FOR_HUMAN_SEND` and their delivery records remain `NOT_SENT`.

Human roles are required for verification, commercial approval, contract approval, and communication approval. AI/runtime outputs remain candidate, proposed, or draft state until the named human action is recorded. Stage 2 disposition is checked by capability invocation and is not changed by this implementation.
