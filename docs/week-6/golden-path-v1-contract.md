# Golden Path v1 Contract

The repeatable command is:

```bash
make golden-path-v1
```

It resets an isolated configured test database, seeds the canonical fixture, and writes `artifacts/golden-path-v1-result.json`. The result must print the fixture name/version/hash, canonical project/application, bootstrap events, document/version IDs, verified assertion IDs, package ID/hash, approval actor, preparation revision, portal snapshot, reconciliation, precheck, handoff, audit/correlation IDs, and `machine_final_submit: false`.

The contract is intentionally Week 6 scoped. Week 7 findings may be recorded by shared models, but Finding closure, recurrence, resubmission, and Week 10 behavior are not prerequisites for this v1 pass.
