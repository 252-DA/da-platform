# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.11.32 AS uv
FROM python:3.10-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Same parser system deps as packages-ai/Dockerfile — document-inspector
# uses the same AdaptivePdfParser/DocxParser/PptxParser/MarkdownParser.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libmagic1 \
        build-essential \
        zlib1g-dev \
        libgl1 \
        libglib2.0-0 \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-vie \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=uv /uv /uvx /bin/

COPY packages-ai/pyproject.toml packages-ai/uv.lock* packages-ai/README.md /app/packages-ai/
COPY packages-ai/src/ /app/packages-ai/src/
COPY document-inspector/pyproject.toml document-inspector/uv.lock* document-inspector/README.md /app/document-inspector/
COPY document-inspector/src/ /app/document-inspector/src/

WORKDIR /app/document-inspector
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

RUN .venv/bin/python -c "from tokenizers import Tokenizer; Tokenizer.from_pretrained('BAAI/bge-m3', revision='5617a9f61b028005a4858fdac845db406aefb181').save('/app/bge-m3-tokenizer.json')"

FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libmagic1 \
        libgl1 \
        libglib2.0-0 \
        poppler-utils \
        tesseract-ocr \
        tesseract-ocr-eng \
        tesseract-ocr-vie \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/document-inspector/.venv /app/.venv
COPY --from=builder /app/bge-m3-tokenizer.json /app/bge-m3-tokenizer.json
ENV CHUNKER__TOKENIZER_PATH=/app/bge-m3-tokenizer.json

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8002

# python -m thay vì console-script "uvicorn" — venv không relocatable giữa
# hai build stage, xem note trong embedding-service/Dockerfile.
CMD ["python", "-m", "uvicorn", "document_inspector.delivery.app:app", "--host", "0.0.0.0", "--port", "8002"]
