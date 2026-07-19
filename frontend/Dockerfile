# syntax=docker/dockerfile:1

# =============================================================================
# Frontend image (CLAUDE.md §2, §5.1 — multi-stage, non-root)
# Stage 1 builds the static bundle with Vite; stage 2 serves it with an
# unprivileged nginx (runs as uid 101, listens on 8080).
# =============================================================================

# ---- Build -------------------------------------------------------------------
FROM node:20-alpine AS build

WORKDIR /app

# Vite inlines VITE_* variables at build time, so the API base URL must be known
# here. Defaults to the local backend; override with
# `--build-arg VITE_API_BASE_URL=...` for other environments.
ARG VITE_API_BASE_URL=http://localhost:8000/api/v1
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Install dependencies from the lockfile first so the layer caches across
# source-only changes.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- Serve -------------------------------------------------------------------
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

# SPA-aware config (client-side routing falls back to index.html).
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://localhost:8080/ || exit 1
