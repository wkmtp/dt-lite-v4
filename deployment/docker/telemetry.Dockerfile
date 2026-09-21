# DT-Lite Telemetry Service
FROM python:3.11-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

COPY services/telemetry /build/telemetry
COPY packages/common /build/common
COPY packages/schemas /build/schemas

FROM python:3.11-slim AS runtime

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY --from=builder /build/telemetry /app/telemetry
COPY --from=builder /build/common /app/common
COPY --from=builder /build/schemas /app/schemas

RUN groupadd -r dtlite && useradd -r -g dtlite dtlite
USER dtlite

EXPOSE 8080

ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=${DATABASE_URL}
ENV REDIS_URL=${REDIS_URL}
ENV JWT_SECRET_REF=${JWT_SECRET_REF}

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

CMD ["uvicorn", "services.telemetry.main:app", "--host", "0.0.0.0", "--port", "8080"]
