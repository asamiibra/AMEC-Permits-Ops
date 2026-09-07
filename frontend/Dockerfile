FROM node:22-alpine@sha256:c610fcdfb1d5b4740dd70c284ed3cb16bb857e0f7166196e36a5501df7a3aa32 AS builder

WORKDIR /app

ARG VITE_ENTRA_TENANT_ID
ARG VITE_ENTRA_WEB_CLIENT_ID
ARG VITE_ENTRA_API_CLIENT_ID
ARG VITE_API_URL
ARG RELEASE_SHA

RUN set -eu; \
    test -n "$VITE_ENTRA_TENANT_ID"; \
    test -n "$VITE_ENTRA_WEB_CLIENT_ID"; \
    test -n "$VITE_ENTRA_API_CLIENT_ID"; \
    test -n "$VITE_API_URL"; \
    printf '%s\n' "$RELEASE_SHA" | grep -Eq '^[0-9a-f]{40}$'; \
    printf '%s\n' "$VITE_ENTRA_TENANT_ID" | grep -Eq '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$'; \
    printf '%s\n' "$VITE_ENTRA_WEB_CLIENT_ID" | grep -Eq '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$'; \
    printf '%s\n' "$VITE_ENTRA_API_CLIENT_ID" | grep -Eq '^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$'; \
    test "$VITE_ENTRA_WEB_CLIENT_ID" != "$VITE_ENTRA_API_CLIENT_ID"

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ENV VITE_ENTRA_TENANT_ID="$VITE_ENTRA_TENANT_ID" \
    VITE_ENTRA_WEB_CLIENT_ID="$VITE_ENTRA_WEB_CLIENT_ID" \
    VITE_ENTRA_API_CLIENT_ID="$VITE_ENTRA_API_CLIENT_ID" \
    VITE_API_URL="$VITE_API_URL"

RUN npm run build

FROM nginx:1.27-alpine@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10 AS runtime

ARG RELEASE_SHA
ARG BUILD_ID=UNSET

LABEL org.opencontainers.image.source="https://github.com/asamiibra/AMEC-Permits-Ops" \
      org.opencontainers.image.revision="${RELEASE_SHA}"

COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /app/dist/ /usr/share/nginx/html/

RUN set -eu; \
    printf '%s\n' "$RELEASE_SHA" | grep -Eq '^[0-9a-f]{40}$'; \
    printf '%s\n' "$BUILD_ID" | grep -Eq '^[A-Za-z0-9_.:-]{1,128}$'; \
    printf '{"release_sha":"%s","build_id":"%s"}\n' "$RELEASE_SHA" "$BUILD_ID" > /usr/share/nginx/html/release.json

RUN mkdir -p \
      /tmp/client_temp \
      /tmp/proxy_temp \
      /tmp/fastcgi_temp \
      /tmp/uwsgi_temp \
      /tmp/scgi_temp \
    && chown -R nginx:nginx \
      /tmp/client_temp \
      /tmp/proxy_temp \
      /tmp/fastcgi_temp \
      /tmp/uwsgi_temp \
      /tmp/scgi_temp \
      /usr/share/nginx/html

USER nginx
EXPOSE 8080
