# Cross-module propagation closure

Master-content changes now use one durable `MasterContentChangeEvent` contract. The event carries business reference, category snapshot, change kind/reason, materiality, source hash, and exact version identity. `MasterContentDependency` is an explicit registry; downstream records do not copy master bytes.

```text
ONE CANONICAL FORM LIBRARY
        |
        +--> Dashboard
        +--> Administration / Forms
        +--> AMEC Work
        +--> Business Development
        +--> Permit workflows
```

Administration `/admin/forms` is an access and management projection of the same canonical `MasterContentItem(content_type=FORM)` records used by the other surfaces. It uses the shared controller, editor, version history, and download routes; an ordinary Form upload with no explicit dependency does not create a spurious Issue, Work item, or Notification.

Material current-version changes are projected through existing canonical records:

- Forms and Reports can bind `FormTemplate`, `ReportDefinition`, or `GeneratedReport` dependencies.
- Engineering Works bind `EngineeringReview` or `EngineeringReviewRun` dependencies.
- Stale project dependencies create existing `Finding` records, existing `WorkflowTask` records, and existing `NotificationEvent` records.
- `MasterContentEventDelivery` provides event/target/recipient deduplication.
- `/api/master-content/eligible?use=ENGINEERING_AI` returns only active, current, reviewed, hash-verified Engineering Works.
- Definitions remain structured `DefinitionEntry`/`DefinitionRevision` records and emit the same event family for notification and future consumers.

The proof is recorded in `artifacts/owner-dashboard-sor/cross-module-runtime-result.json` and the integration result files in the same directory.
