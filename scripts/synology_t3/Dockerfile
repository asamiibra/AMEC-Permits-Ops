FROM python:3.12-slim-trixie@sha256:876416ecde9aca2bcc90e1fb0c7a9500bbf749f5788b70f82d4c5a5c2357f8b4

ARG ACCEPTED_V23_SHA
RUN test "$ACCEPTED_V23_SHA" = "4925518b35b58956aaa5870f226af5e57d14b610"

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/opt/proposalops
WORKDIR /opt/proposalops

COPY backend /opt/proposalops/backend
COPY scripts/synology_t3 /opt/proposalops/scripts/synology_t3

RUN python -m pip install --no-cache-dir --disable-pip-version-check "smbprotocol==1.15.0" \
    && python -m compileall -q backend/app/storage scripts/synology_t3 \
    && python -c 'import smbclient; print(smbclient.__version__ if hasattr(smbclient, "__version__") else "smbclient-loaded")'

RUN groupadd --gid 10001 proposalops \
    && useradd --uid 10001 --gid 10001 --create-home --home-dir /home/proposalops --shell /usr/sbin/nologin proposalops \
    && chown -R 10001:10001 /opt/proposalops

LABEL org.opencontainers.image.revision="4925518b35b58956aaa5870f226af5e57d14b610" \
      org.opencontainers.image.source="https://github.com/asamiibra/AMEC-Permits-Ops" \
      org.opencontainers.image.platform="linux/amd64" \
      org.opencontainers.image.synthetic-only="true"

USER 10001:10001
