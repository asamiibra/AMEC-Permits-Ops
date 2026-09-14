FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund

COPY . .

ARG VITE_API_URL
ARG VITE_ENTRA_TENANT_ID
ARG VITE_ENTRA_WEB_CLIENT_ID
ARG VITE_ENTRA_API_CLIENT_ID
ENV VITE_API_URL=$VITE_API_URL \
    VITE_ENTRA_TENANT_ID=$VITE_ENTRA_TENANT_ID \
    VITE_ENTRA_WEB_CLIENT_ID=$VITE_ENTRA_WEB_CLIENT_ID \
    VITE_ENTRA_API_CLIENT_ID=$VITE_ENTRA_API_CLIENT_ID

RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
