# Hosted / local furniture_cad jobs worker.
#
# Local:
#   docker build -t furniture-cad-worker -f lab/furniture_cad/Dockerfile lab/furniture_cad
#   docker run --rm -p 8787:8787 -e ANTHROPIC_API_KEY -e WORKER_JOBS_TOKEN=dev \
#     furniture-cad-worker
#
# Fly.io: see docs/deploy-worker.md and lab/furniture_cad/fly.toml
#
# build123d/OCP wheels are large; first build can take several minutes.

FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libx11-6 libxext6 libxrender1 curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY contracts ./contracts
COPY examples ./examples

RUN pip install --no-cache-dir -e ".[worker]"

ENV FURNITURE_CAD_MAX_ROUNDS=8 \
    FURNITURE_CAD_MAX_TOKENS=16000 \
    FURNITURE_CAD_MAX_SPEND_USD_PER_JOB=2.0 \
    FURNITURE_CAD_MAX_SPEND_USD_PER_DAY=25.0 \
    FURNITURE_CAD_MAX_WALL_TIME_S=900 \
    FURNITURE_CAD_MODEL=claude-haiku-4-5 \
    PYTHONUNBUFFERED=1 \
    PORT=8787 \
    JOBS_ROOT=/data/jobs

RUN mkdir -p /data/jobs

EXPOSE 8787

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-8787}/health" || exit 1

# Default: job HTTP service (shop-grade Create). Override CMD for CLI one-shots.
CMD ["sh", "-c", "python -m furniture_cad jobs --host 0.0.0.0 --port ${PORT:-8787} --root ${JOBS_ROOT:-/data/jobs}"]
