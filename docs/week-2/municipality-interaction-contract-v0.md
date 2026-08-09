# Municipality interaction contract v0

The Permit Authority Simulator is a local synthetic surface. It exposes configuration, draft save/reopen, validation, and precheck results through explicit endpoints.

Supported operation categories are `READ_APPLICATION`, `READ_STATUS`, `READ_COMMENTS`, `READ_CONFIGURATION`, `PREPARE_DRAFT`, `UPLOAD_ATTACHMENT`, and `VALIDATE_DRAFT`. The simulator includes stable tab keys, field keys, dropdown codes/labels, grid row identity, attachment categories, validation findings, and precheck states.

`SUBMIT_APPLICATION` is intentionally absent. The municipality adapter remains read-only and the final action is represented only by human confirmation evidence.
