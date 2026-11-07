# Phase 0 worker stub — Local Docker (choice A).
# Limits match contracts/tools.v1.json; override via env.
#
#   docker build -t furniture-cad-worker -f lab/furniture_cad/Dockerfile lab/furniture_cad
#   docker run --rm -e ANTHROPIC_API_KEY -v "$PWD/out:/work" furniture-cad-worker \
#     run --work /work --script /app/examples/tools/bookshelf_offline.json
#
# build123d/OCP wheels are large; first build can take several minutes.

FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libx11-6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY contracts ./contracts
COPY examples ./examples

RUN pip install --no-cache-dir -e ".[dev]" && pip install --no-cache-dir anthropic

# Caps from Phase 0 freeze / tools.v1.json
ENV FURNITURE_CAD_MAX_ROUNDS=8 \
    FURNITURE_CAD_MAX_TOKENS=16000 \
    FURNITURE_CAD_MAX_SPEND_USD_PER_JOB=2.0 \
    FURNITURE_CAD_MAX_SPEND_USD_PER_DAY=25.0 \
    FURNITURE_CAD_MAX_WALL_TIME_S=900 \
    PYTHONUNBUFFERED=1

WORKDIR /work
ENTRYPOINT ["python", "-m", "furniture_cad"]
CMD ["run", "--contract"]
