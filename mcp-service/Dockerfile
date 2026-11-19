# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.11.32 AS uv
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# libmagic1: python-magic (document-chunk base dependency) needs it at
# import time even though mcp-service never parses raw files itself.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libmagic1 \
        zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=uv /uv /uvx /bin/

COPY service-sdk /app/service-sdk
COPY packages-ai/pyproject.toml packages-ai/uv.lock* packages-ai/README.md /app/packages-ai/
COPY packages-ai/src/ /app/packages-ai/src/
COPY mcp-service/pyproject.toml mcp-service/uv.lock* mcp-service/README.md /app/mcp-service/
COPY mcp-service/src/ /app/mcp-service/src/

WORKDIR /app/mcp-service
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends libmagic1 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/mcp-service/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8001

# python -m thay vì console-script "mcp-service" — venv không relocatable
# giữa hai stage build, xem note trong embedding-service/Dockerfile.
CMD ["python", "-m", "mcp_service.delivery.server"]
