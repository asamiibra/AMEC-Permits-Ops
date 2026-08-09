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
