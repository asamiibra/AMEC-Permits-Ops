# AMEC Work separation

AMEC Work remains the task queue and continues to use `WorkflowTask`. Issues are findings/exceptions and may have a related task, but an Issue row is not itself a task. Notifications are event awareness and may exist without an Issue or task. Acknowledging a notification records `acknowledged_at` and leaves the related task status unchanged.
