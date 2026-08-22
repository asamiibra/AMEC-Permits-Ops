#!/usr/bin/env bash
set -euo pipefail
python -m backend.app.migrate
exec python -m backend.app.provision_db_roles
