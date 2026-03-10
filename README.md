# Nerdcast Finder

Semantic search engine for podcast episode segments using embeddings and FAISS indexing.

## Quick Start

```bash
# Windows (PowerShell)
.\install.ps1
.\start.ps1

# Linux/macOS
chmod +x install.sh start.sh
./install.sh
./start.sh
```

Backend runs at http://localhost:8000 | Frontend at http://127.0.0.1:8050

## Requirements

- Python 3.11+
- FFmpeg

Installation:
- Windows: `choco install ffmpeg` or download from https://ffmpeg.org/download.html
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

## Architecture

**Backend (FastAPI)**
- Whisper large-v3 for audio transcription
- sentence-transformers (all-MiniLM-L6-v2) for embeddings
- FAISS for similarity search indexing
- SQLite for segment storage
- REST API for search queries

**Frontend (Dash)**
- Search interface with similarity scoring

## Setup & Usage

### 1. Install Dependencies

```bash
# Automated (recommended)
./install.ps1          # Windows
./install.sh           # Linux/macOS

# Manual
cd backend && pip install -r requirements.txt && cd ..
cd frontend && pip install -r requirements.txt && cd ..
```

### 2. Add Podcast Files

Place audio files (`.mp3`, `.wav`, `.m4a`) in:
backend/data/podcasts/
```

### 3. Run Ingestion Pipeline

```bash
cd backend
python -m scripts.ingest_podcasts
```

Transcribes audio, generates embeddings, and builds the FAISS index. This can take a while depending on audio file size and hardware. GPU recommended for faster transcription.

### 4. Start Application

```bash
# Auto start (recommended)
./start.ps1          # Windows
./start.sh           # Linux/macOS

# Manual start
cd backend && python -m app.main
# In another terminal:
cd frontend && python app.py
```

## API

**Search Endpoint:** `GET /api/search`

Query parameters:
- `q` (required): search query
- `top_k` (optional): number of results (default: 10, max: 50)

Response:
```json
[
  {
    "episode": "episode_name",
    "excerpt": "relevant text snippet...",
    "score": 0.8734
  }
]
```

Example:
```bash
curl "http://localhost:8000/api/search?q=artificial%20intelligence&top_k=5"
```

## Configuration

Edit `backend/app/config/settings.py`:

```python
WHISPER_MODEL = "large-v3"              # base, small, medium, large, large-v2, large-v3
EMBEDDING_MODEL = "all-MiniLM-L6-v2"    # or: intfloat/multilingual-e5-base
CHUNK_SIZE = 750                         # Characters per segment
TRANSCRIPTION_LANGUAGE = "pt"            # Language code or None for auto-detect
DEFAULT_TOP_K = 10
MAX_TOP_K = 50
```

See [ARCHITECTURE.md](backend/ARCHITECTURE.md) for details.

## Deployment

### Google Cloud Run

```bash
cp .env.example .env
# Edit .env with GCP_PROJECT_ID, GCS_BUCKET, etc.

python -m backend.pipelines.deploy.build_and_deploy         # Build & deploy
python -m backend.pipelines.deploy.build_and_deploy --build-only  # Build only
python -m backend.pipelines.deploy.build_and_deploy --deploy-only # Deploy only
```

Update FAISS index or database:

```bash
python -m backend.pipelines.deploy.upload_to_gcs --deploy       # Upload all + redeploy
python -m backend.pipelines.deploy.upload_to_gcs --db-only      # DB only
python -m backend.pipelines.deploy.upload_to_gcs --index-only   # Index only
```

Service account requires `roles/storage.objectViewer` on GCS bucket.

### Render

Web Service with build command:
```bash
pip install --upgrade pip
pip install -r requirements-prod.txt
```

Start command:
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT --workers 1 --log-level info
```

Environment variables:
- `PORT` (provided by Render)
- `PYTHON_VERSION` (e.g., 3.11)
- `FAISS_INDEX_PATH` (optional)
- `BACKEND_URL` (if frontend deployed separately)
- `LOG_LEVEL` (optional)
- `CORS_ALLOW_ORIGINS` (optional)

Required runtime files:
- `backend/data/faiss_index/podcasts.index`
- `backend/data/faiss_index/embedding_id_mapping.npy`
- `backend/data/podcast_database.db`

## GPU Acceleration

Install PyTorch with CUDA for faster transcription:
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

FAISS GPU support:
```bash
pip uninstall faiss-cpu
pip install faiss-gpu
```

## License

MIT

## Credits

Built with FastAPI, Whisper, sentence-transformers, FAISS, and Dash.
