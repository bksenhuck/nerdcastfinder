# Multi-stage build
FROM python:3.11-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends build-essential gcc git curl ca-certificates libsndfile1 libgomp1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --upgrade pip
RUN pip wheel --wheel-dir=/wheels -r requirements.txt || true

FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 libgomp1 ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN python -m pip install --upgrade pip && pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt || pip install --no-cache-dir -r requirements.txt
COPY . /app
ENV PORT=8080 PYTHONUNBUFFERED=1
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser
EXPOSE 8080
# POC tuning: use 1 worker to avoid duplicating large in-memory
# artifacts (FAISS / model weights). Increase workers or use
# `--preload` only after validating memory and startup behavior.
# Use a large timeout to allow heavy index loading during cold-starts.
CMD ["gunicorn","-k","uvicorn.workers.UvicornWorker","-w","1","-b","0.0.0.0:8080","--timeout","1000","backend.app.main:app"]