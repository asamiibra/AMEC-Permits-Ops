# Source18 and baseline causality

Control and integrated candidate were both run against fresh PostgreSQL databases with the same `alembic upgrade head` command. Both failed before the Billing migration at the frozen baseline statement that reuses `:value_1` across PostgreSQL `text` and `varchar` contexts:

`psycopg.errors.AmbiguousParameter: inconsistent types deduced for parameter $2`

The baseline mutation from the historical Billing tree changes those bind names. This is classified as `POSTGRESQL_BIND_TYPING_COMPATIBILITY`, not Billing and not Source18. It is excluded from the durable Billing branch.

In a disposable probe only, the offending Source18 index identifier was shortened and the historical baseline bind fix was used. The full chain then applied through `billing_module_closure_v8` successfully. Therefore:

- `SOURCE18_POSTGRES_DEFECT_CAUSALITY=CONFIRMED_PREEXISTING_UNRELATED_TO_BILLING`
- `BILLING_FULL_CHAIN_COMPATIBILITY_PROBE=PASS`
- `SEPARATE_PLATFORM_FIX_REQUIRED=true`
- no Source18 or baseline rewrite is carried in the Billing branch
