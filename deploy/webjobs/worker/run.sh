#!/usr/bin/env bash
set -euo pipefail
exec python -m backend.app.worker
