# Source Intake Visibility

Synthetic Source Intake tests prove:

```text
SourceIntakeBatch / SourceIntakeItem
  → SourceIntakeService.promote_batch
  → create_master_content
  → MasterContentItem + Document + DocumentVersion
  → canonical Dashboard list/detail projection
```

Current and Needs Review promotions create canonical master rows; historical, reference-only, duplicate, and empty-folder observations do not create master rows. FORME.zip was not re-imported.
