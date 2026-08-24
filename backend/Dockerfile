FROM python:3.12-slim-trixie@sha256:876416ecde9aca2bcc90e1fb0c7a9500bbf749f5788b70f82d4c5a5c2357f8b4

ARG RELEASE_SHA

RUN RELEASE_SHA="$RELEASE_SHA" python -c \
    'import os, re, sys; value=os.environ.get("RELEASE_SHA", ""); sys.exit(0 if re.fullmatch(r"[0-9a-f]{40}", value) else 1)'

LABEL org.opencontainers.image.revision="${RELEASE_SHA}" \
      org.opencontainers.image.source="https://github.com/asamiibra/AMEC-Permits-Ops"

ENV RELEASE_SHA="${RELEASE_SHA}" \
    APP_ENV=AZURE-PREPROD \
    SYNTHETIC_ONLY=true \
    REAL_DATA_ALLOWED=false \
    AUTH_MODE=ENTRA \
    ENTRA_REQUIRED_SCOPE=access_as_user \
    STORAGE_PROVIDER=mock \
    SYNOLOGY_MODE=SYNTHETIC \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/workspace \
    SYNTHETIC_TEST_ROOT=/home/proposalops \
    MOCK_SYSTEMS_ROOT=/home/proposalops/mock-systems

WORKDIR /workspace

COPY backend/requirements-runtime.lock /tmp/requirements-runtime.lock
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg unixodbc unixodbc-dev \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && curl -fsSL https://packages.microsoft.com/config/debian/13/prod.list > /etc/apt/sources.list.d/microsoft-prod.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && odbcinst -q -d | grep -F 'ODBC Driver 18 for SQL Server' \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir --require-hashes -r /tmp/requirements-runtime.lock \
    && python -m pip check \
    && rm -f /tmp/requirements-runtime.lock

COPY backend/__init__.py /workspace/backend/__init__.py
COPY backend/app /workspace/backend/app
COPY backend/migrations /workspace/backend/migrations

RUN groupadd --gid 10001 proposalops \
    && useradd --uid 10001 --gid 10001 --create-home \
       --home-dir /home/proposalops --shell /usr/sbin/nologin proposalops \
    && mkdir -p /home/proposalops/mock-systems /home/proposalops/synthetic-data \
    && chown -R 10001:10001 /home/proposalops

USER 10001:10001
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
