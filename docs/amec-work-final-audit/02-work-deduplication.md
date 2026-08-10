# Work deduplication

Linked Finding and WorkflowTask records use `FINDING:<id>` as one canonical action key. The WorkflowTask projection wins when both sources exist; independent lifecycle actions retain their own affected-entity/action key. The resulting queue contains zero duplicate actionable rows.
