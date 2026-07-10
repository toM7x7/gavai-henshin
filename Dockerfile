# Cloud Run container for the henshin API/dashboard server.
# The existing Python server is the contract source of truth
# (docs/web-service-readiness-2026-05-02.md); this image lifts it as-is.
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .

# Runtime data the server reads from disk at request time.
COPY schemas ./schemas
COPY examples ./examples
COPY viewer ./viewer
COPY tools/run_henshin.py ./tools/run_henshin.py

ENV APP_ENV=cloud \
    STORE_DRIVER=json \
    ARTIFACT_STORE_DRIVER=local \
    LIVE_STATE_DRIVER=memory \
    QUEUE_DRIVER=inline

# sessions/ is ephemeral on Cloud Run; run with max-instances=1 until the
# SuitStore/TrialStore drivers land (see docs/cloud-architecture-2026-07.md).
RUN mkdir -p sessions

EXPOSE 8080
CMD ["sh", "-c", "python tools/run_henshin.py serve-dashboard --port ${PORT:-8080} --root ."]
