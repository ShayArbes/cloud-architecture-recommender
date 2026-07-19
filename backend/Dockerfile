# syntax=docker/dockerfile:1

# =============================================================================
# Backend image (CLAUDE.md §2, §5.1 — multi-stage, slim, non-root)
# Stage 1 installs the project (and its dependencies) into an isolated venv;
# stage 2 copies only that venv into a minimal runtime image.
# =============================================================================

# ---- Builder -----------------------------------------------------------------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /build

# The runtime stage copies this venv verbatim, so it must hold everything the
# app needs to import.
RUN python -m venv /opt/venv

# Copy only what the build needs, then install. Dependency resolution is the
# slow step; keeping it in its own layer lets Docker cache it across changes.
COPY pyproject.toml ./
COPY app ./app
RUN pip install .

# ---- Runtime -----------------------------------------------------------------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# curl backs the container HEALTHCHECK below; nothing else is added to keep the
# attack surface small.
RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

COPY --from=builder /opt/venv /opt/venv

USER appuser
WORKDIR /home/appuser

EXPOSE 8000

# Mirrors GET /health (CLAUDE.md §6); returns 200 while the process is alive.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
