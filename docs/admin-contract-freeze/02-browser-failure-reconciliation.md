# Browser failure reconciliation

Prior reports of 57/12 and 20/3 were treated as observations, not truth. The current real-stack suite was rerun against local Vite, FastAPI, and PostgreSQL.

Three failures were reproduced and explained:

- Forms and Dashboard version assertions exposed a missing visible Version column. The UI now renders the canonical version label in both tables.
- Administration Contract Setup exposed a heading mismatch. The configuration heading and the Contracts subsection are now both explicit.
- Engineering Work creation was blocked by the required Engineering Source Type omitted by the existing golden test. The test now supplies the governed field.

Final result: **23 passed, 0 failed; Admin/Contract golden failures 0; unexplained failures 0**. See [browser-failure-reconciliation.json](../../artifacts/admin-contract-freeze/browser-failure-reconciliation.json).

