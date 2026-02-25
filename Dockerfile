# --- Stage 1: Build wheels ---
FROM python:3.11-slim AS builder
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc git curl ca-certificates libsndfile1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip
RUN pip wheel --wheel-dir=/wheels -r requirements.txt || true

# --- Stage 2: Final image ---
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /wheels /wheels
COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
    || pip install --no-cache-dir -r requirements.txt

# --- Copy backend + frontend + search artifacts ---
COPY backend /app/backend
COPY frontend /app/frontend
COPY backend/data/faiss_index /app/backend/data/faiss_index
# Note: `nerdcasts.db` is intentionally NOT copied into the image here.
# The POC runtime will download the DB from GCS if `FAISS_GCS_URI` or a
# DB-specific env var is provided, or you can embed the DB in the image
# by adding a COPY line here (not recommended for large binaries).

# --- Pre-download sentence-transformers model into the image ---
# Avoids runtime HuggingFace downloads (rate-limits / cold-start latency).
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-mpnet-base-v2'); print('Model cached.')"

# --- Copy remaining files (overwrite duplicates if any) ---
COPY . /app

# --- Environment + permissions ---
ENV PORT=8080 PYTHONUNBUFFERED=1
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8080

# --- CMD for Gunicorn ---
CMD ["gunicorn","-k","uvicorn.workers.UvicornWorker","-w","1","-b","0.0.0.0:8080","--timeout","1000","backend.app.main:app"]