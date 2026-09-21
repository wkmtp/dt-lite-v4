# DT-Lite AI Service
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

COPY services/ai /build/ai

FROM python:3.11-slim AS runtime

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY --from=builder /build/ai /app/ai
COPY services/common /app/common
COPY packages/schemas /app/schemas

RUN groupadd -r dtlite && useradd -r -g dtlite dtlite
USER dtlite

EXPOSE 8080

ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=${DATABASE_URL}
ENV REDIS_URL=${REDIS_URL}
ENV AI_OPENAI_API_KEY=${AI_OPENAI_API_KEY}
ENV AI_EMBEDDING_MODEL=${AI_EMBEDDING_MODEL:-text-embedding-3-large}

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "services.ai.main:app", "--host", "0.0.0.0", "--port", "8080"]
