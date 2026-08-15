# Register API inventory

Canonical route: `GET /api/bd/proposals`.

Query contract: `q`, `client`, `activity`, `location`, `stage`, and derived `lane` (`ALL`, `NEED_ACTION`, `AUTHORITY_REVIEW`, `READY_CLOSE`). The endpoint builds one backend row projection, applies search/stage/location, computes lane counts from those same rows, and then filters the requested lane. No frontend count or second datastore exists.

Primary row columns: Proposal Description (`proposal`), Project Ref (`project_ref`), Stage (`stage`), Amount (`amount`), Last Activity (`last_activity`), and Open (`id`). Secondary context is Client, Current Owner, and Next Action. Amount is `proposal_fields.price`; missing values are rendered as `Not set`. Last Activity is the current Opportunity material-activity timestamp.

Detail route: `GET /api/bd/proposals/{proposal_id}`. Compatibility routes remain outside this owner workspace.
