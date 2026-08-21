FROM node:22-alpine AS builder

WORKDIR /app

ARG VITE_ENTRA_TENANT_ID
ARG VITE_ENTRA_WEB_CLIENT_ID
ARG VITE_ENTRA_API_CLIENT_ID
ARG VITE_API_URL

RUN set -eu; \
    test -n "$VITE_ENTRA_TENANT_ID"; \
    test -n "$VITE_ENTRA_WEB_CLIENT_ID"; \
    test -n "$VITE_ENTRA_API_CLIENT_ID"; \
    test -n "$VITE_API_URL"; \
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

FROM nginx:1.27-alpine AS runtime

COPY nginx.conf /etc/nginx/nginx.conf
COPY --from=builder /app/dist/ /usr/share/nginx/html/

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
