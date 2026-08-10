# Full Browser Suite Reconciliation

## Targeted historical failures

Source: `artifacts/master-realignment/full-browser-regression.json`. The 19 failures were limited to retired PermitOps/Permit labels, the retired Permit Preparer/four-assistant owner model, and superseded navigation/timing expectations. The two documented target specs now run 28 tests with 28 passed and 0 failed.

## Full current browser-e2e

The full run exercised 117 tests: 84 passed and 33 failed. The remaining failures are outside the 19-target repair and are primarily stale assertions for removed global Arabic controls, old expansion enum copy, old legacy route expectations, retired Week evidence surfaces, and legacy role selectors. They are not silently counted as product passes.

## Full current real-stack

The full run exercised 33 tests: 23 passed and 10 failed. The failures are stale current-suite assertions for the removed global Arabic switch, retired Permit Preparer, old headings/status labels, and legacy direct-route assumptions. The universal current material crawl separately passed 3/3 tests locally.

## Genuine product failures

1. Incomplete `/api/proposals-main` payloads can still trigger an `OPEN_PROPOSALS` projection TypeError.
2. The deployed Vercel release is behind local: 28 deployed console 404s on retired Admin aliases and one stale `WorkflowTask` label.

Evidence: `artifacts/master-realignment/full-browser-regression-realignment-final.json`, `artifacts/universal-design-audit/local-deployed-parity.json`, and `artifacts/universal-design-audit/genuine-product-failures.json`.
