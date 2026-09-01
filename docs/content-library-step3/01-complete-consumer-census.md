# Complete executable consumer census

The census searched Python services, API routers, models, tests, and frontend calls for Master Content, Document/DocumentVersion, Definitions, bindings, exact IDs, templates, rendering, preparation, submission, completion, handover, billing, and reporting.

The machine-readable source of truth is `02-consumer-classification-matrix.json`. It records 26 discovered executable surfaces. Each row has exactly one required classification and an evidence path. Producer/control surfaces are included so they cannot be mistaken for downstream consumers.

Primary traces:

- Proposal: `backend/app/services/proposal_workspace.py`, `backend/app/api/bd_proposal_routers.py`
- Contract: `backend/app/services/contract_workspace.py`, `backend/app/api/contract_workspace_routers.py`
- Shared forms: `backend/app/api/shared_domain_routers.py`, `backend/app/services/shared_domains.py`
- Completion: `backend/app/api/completion_asbuilt_routers.py`
- Preparation/submission: `backend/app/api/preparation_submission_routers.py`, `backend/app/services/week9.py`
- Project Engineering: `backend/app/api/project_engineering_routers.py`
- Week 4–5 rendering: `backend/app/api/week45_routers.py`, `backend/app/models/week45_entities.py`
- Synthetic expansion rendering: `backend/app/expansion/runtime.py`, `backend/app/models/expansion_entities.py`
- Definitions/retrieval: `backend/app/services/master_content.py`, `backend/app/services/governed_retrieval.py`
