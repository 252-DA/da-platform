# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.11.32 AS uv
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# libgomp1: OpenMP runtime needed by torch/FlagEmbedding at inference time.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libgomp1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=uv /uv /uvx /bin/

COPY service-sdk /app/service-sdk
COPY embedding-service/pyproject.toml embedding-service/uv.lock* embedding-service/README.md /app/embedding-service/
COPY embedding-service/src/ /app/embedding-service/src/

WORKDIR /app/embedding-service
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/embedding-service/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Model không bake vào image — mount named volume Hugging Face cache tại
# runtime (docker-compose: HF_HOME hoặc TRANSFORMERS_CACHE trỏ vào volume).
EXPOSE 50051 9095

# Không dùng console-script "embedding-service" — uv sync tạo venv với
# shebang absolute path trỏ về /app/embedding-service/.venv (nơi build ở
# stage builder), venv không relocatable nên script vỡ sau khi COPY sang
# /app/.venv ở stage cuối ("no such file or directory" dù file tồn tại).
# python -m tránh hẳn vấn đề này — cùng pattern worker/Dockerfile và
# packages-ai/Dockerfile đang dùng.
CMD ["python", "-m", "embedding_service.delivery.server"]
