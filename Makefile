PYTHON ?= python3
PIP ?= pip

install:
	$(PIP) install -r backend/requirements.txt

migrate:
	PYTHONPATH=. $(PYTHON) -m alembic -c alembic.ini upgrade head

seed:
	$(PYTHON) -m backend.app.seed.cli seed

test:
	PYTHONPATH=. $(PYTHON) -m pytest backend/tests -q

storage-lab-up:
	docker compose -f dev/storage-lab/docker-compose.storage.yml up --build -d

storage-lab-down:
	docker compose -f dev/storage-lab/docker-compose.storage.yml down

storage-contract:
	PYTHONPATH=. APP_ENV=TEST SYNTHETIC_ONLY=true STORAGE_CONTRACT_PROVIDER=$${STORAGE_CONTRACT_PROVIDER:-smb} SMB_SERVER=$${SMB_SERVER:-127.0.0.1} SMB_PORT=$${SMB_PORT:-1445} SMB_SHARE=$${SMB_SHARE:-ProposalOpsLab} SMB_ROOT=$${SMB_ROOT:-proposalops} SMB_USERNAME=$${SMB_USERNAME:-proposalops_rw} SMB_PASSWORD=$${SMB_PASSWORD:-proposalops_rw_dev} SMB_AUTH_MODE=$${SMB_AUTH_MODE:-ntlm} SMB_REQUIRE_SIGNING=$${SMB_REQUIRE_SIGNING:-true} $(PYTHON) -m pytest backend/tests/test_binary_store_contract.py backend/tests/test_document_storage_service.py backend/tests/test_smb_integration.py -q

up:
	docker compose up --build -d

down:
	docker compose down

reset:
	docker compose down -v
	$(PYTHON) -m backend.app.seed.cli reset

frontend-test:
	cd frontend && npm test -- --run

spike:
	PYTHONPATH=. $(PYTHON) -m backend.app.seed.spike

canonical-fixture-check:
	PYTHONPATH=. $(PYTHON) backend/scripts/canonical_fixture_check_runner.py

golden-path-v1:
	PYTHONPATH=. $(PYTHON) backend/scripts/golden_path_v1.py

golden-path-v2:
	PYTHONPATH=. $(PYTHON) backend/scripts/golden_path_v2.py

week11-12-demo:
	DATABASE_URL=sqlite:///./week11_12_demo.db APP_ENV=TEST SYNTHETIC_ONLY=true PYTHONPATH=. $(PYTHON) backend/scripts/week11_12_demo.py

acceptance-rehearsal:
	PYTHONPATH=. $(PYTHON) backend/scripts/acceptance_rehearsal.py

week9-independent:
	PYTHONPATH=. $(PYTHON) backend/scripts/week9_independent_reconciliation.py

supported-coverage:
	PYTHONPATH=. $(PYTHON) backend/scripts/supported_coverage_check.py

registry-safety:
	PYTHONPATH=. $(PYTHON) backend/scripts/registry_and_safety_check.py

expansion-fixture-check:
	PYTHONPATH=. $(PYTHON) backend/scripts/expansion_fixture_check.py

expansion-evidence:
	PYTHONPATH=. $(PYTHON) backend/scripts/expansion_evidence.py

pre-g10-reconcile:
	PYTHONPATH=. $(PYTHON) backend/scripts/pre_g10_reconcile.py
