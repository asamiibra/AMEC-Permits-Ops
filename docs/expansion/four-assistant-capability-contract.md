# Four assistant capability contract

The only canonical assistant identifiers are:

- `BD_ASSISTANT`
- `ADMIN_ASSISTANT`
- `ENGINEERING_REVIEW_ASSISTANT`
- `PROJECT_PERMIT_COORDINATION_ASSISTANT`

They are bounded views over one governed substrate. E1 registers metadata only: supported requirement IDs, input/output types, required human authority, external-action policy, and Stage 2 disposition. The `A15-08` safe default prevents “Junior Engineer AI” from becoming a fifth assistant.
