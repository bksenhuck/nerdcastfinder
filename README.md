# Nerdcast Finder 🎙️

A semantic search MVP for finding podcast episode segments that mention specific topics.

> **🚀 Quick Start**: After setup, run `.\start.ps1` (Windows) or `./start.sh` (Linux/macOS) to start both backend and frontend. See [QUICKSTART.md](QUICKSTART.md) for details.

## Architecture

**Backend (FastAPI)**
- Transcribes audio using Whisper large-v3
- Generates embeddings using sentence-transformers
- Stores segments in SQLite
- Indexes with FAISS for fast similarity search
- Exposes REST API for search

**Frontend (Dash)**
- Minimal search interface
- Displays results with similarity scores

---

## Tech Stack

### Backend
- FastAPI
- SQLite (SQLAlchemy)
- FAISS
- sentence-transformers (all-MiniLM-L6-v2)
- Whisper large-v3
- Python 3.11+

### Frontend
- Dash (Plotly)
- dash-bootstrap-components

---

## Project Structure

```
nerdcastfinder/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config/
│   │   │   └── settings.py      # Centralized configuration
│   │   ├── api/
│   │   │   └── search.py        # Search endpoint
│   │   ├── services/
│   │   │   ├── transcription_service.py
│   │   │   ├── embedding_service.py
│   │   │   └── search_service.py
│   │   ├── db/
│   │   │   ├── models.py        # SQLAlchemy models
│   │   │   └── session.py       # Database session
│   │   └── utils/
│   │       ├── text_utils.py    # Text processing utilities
│   │       ├── file_utils.py    # File system utilities
│   │       └── logger.py        # Logging utilities
│   ├── scripts/
│   │   └── ingest_podcasts.py   # Ingestion pipeline
│   ├── data/
│   │   ├── podcasts/            # Place audio files here
│   │   ├── faiss_index/         # FAISS index storage
│   │   └── nerdcasts.db         # SQLite database
│   ├── requirements.txt
│   ├── start_backend.ps1        # Backend quick start
│   └── ARCHITECTURE.md          # Code organization docs
│
├── frontend/
│   ├── app.py                   # Dash application
│   ├── requirements.txt
│   └── start_frontend.ps1       # Frontend quick start
│
├── start.ps1                    # Start both (PowerShell)
├── start.bat                    # Start both (Batch)
├── start.sh                     # Start both (Linux/macOS)
├── install.ps1                  # Install dependencies (PowerShell)
├── install.bat                  # Install dependencies (Batch)
├── install.sh                   # Install dependencies (Linux/macOS)
├── QUICKSTART.md                # Quick start guide
└── README.md
```

---

## Setup

### Prerequisites

1. **Python 3.11+**
2. **FFmpeg** (required by Whisper for audio processing)

   **Windows:**
   ```powershell
   # Using chocolatey
   choco install ffmpeg
   
   # Or download from: https://ffmpeg.org/download.html
   ```

   **macOS:**
   ```bash
   brew install ffmpeg
   ```

   **Linux:**
   ```bash
   sudo apt install ffmpeg  # Debian/Ubuntu
   ```

### Installation

1. **Clone or navigate to the project**
   ```powershell
   cd nerdcastfinder
   ```

2. **Create a virtual environment** (recommended)
   ```powershell
   python -m venv venv
   
   # Activate (Windows)
   .\venv\Scripts\activate
   
   # Activate (macOS/Linux)
   source venv/bin/activate
   ```

3. **Install all dependencies**

   **Option A: Automated Install (Recommended)**
   
   ```powershell
   # Windows PowerShell
   .\install.ps1
   
   # Windows Command Prompt
   .\install.bat
   ```
   
   This script automatically installs all backend and frontend dependencies.

   **Option B: Manual Install**
   
   ```powershell
   # Backend dependencies
   cd backend
   pip install -r requirements.txt
   cd ..
   
   # Frontend dependencies
   cd frontend
   pip install -r requirements.txt
   cd ..
   ```

---

## Usage

### 1. Add Podcast Audio Files

Place your podcast audio files (`.mp3`, `.wav`, `.m4a`, etc.) in:
```

## Deploy no Render

Resumo mínimo para rodar em modo runtime-only (consulta FAISS)

- Tipo de serviço: **Web Service** (FastAPI uvicorn)
- Build command (Render):

```bash
pip install --upgrade pip
pip install -r requirements-prod.txt
```

- Start command (Render):

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT --workers 1 --log-level info
```

- Variáveis de ambiente necessárias:
   - `PORT` (fornecido pelo Render)
   - `PYTHON_VERSION` (ex.: `3.11`)
   - `FAISS_INDEX_PATH` (opcional) — path para `nerdcast.index` ou diretório que contenha `nerdcast.index`. Se não setado, usa `backend/data/faiss_index/nerdcast.index`.
   - `BACKEND_URL` (se o frontend for deployado separadamente)
   - `LOG_LEVEL` (opcional, ex.: `INFO`, `DEBUG`)
   - `CORS_ALLOW_ORIGINS` (opcional, lista CSV de origens para produção)

- Arquivos que precisam existir no runtime:
   - `backend/data/faiss_index/nerdcast.index`  
   - `backend/data/faiss_index/embedding_id_mapping.npy`  
   - `backend/data/nerdcasts.db` (SQLite)

- Observações importantes:
   - O deploy é runtime-only: não execute pipelines de ingestão no ambiente de produção.
   - Garanta que os arquivos acima sejam disponibilizados no filesystem (Persistent Disk no Render ou incluídos na imagem de build).
   - `sentence-transformers` depende de `torch` em runtime — certifique-se de instalar as wheels compatíveis com a versão do Python/OS do Render.

backend/data/podcasts/
```

### 2. Run Ingestion Pipeline

This transcribes audio, generates embeddings, and builds the search index:

```powershell
cd backend
python -m scripts.ingest_podcasts
```

**What it does:**
1. ✅ Initializes SQLite database
2. 🎧 Transcribes all audio files using Whisper
3. 📊 Splits transcripts into ~750 character chunks
4. 🧠 Generates embeddings using sentence-transformers
5. 💾 Stores in database
6. 🔍 Builds FAISS index

**Note:** This can take a while depending on:
- Number and length of audio files
- Whisper model size (large-v3 is comprehensive but slow)
- Your hardware (GPU highly recommended for faster transcription)

### 3. Start the Application

**Option A: Quick Start (Recommended)**

Use the convenience script to start both backend and frontend automatically in separate terminals:

**Windows:**
```powershell
# PowerShell
.\start.ps1

# Or if execution policy blocks .ps1:
.\start.bat
```

**Linux/macOS:**
```bash
# Make executable (first time only)
chmod +x start.sh

# Run
./start.sh
```

This will open two terminal windows:
- **Backend**: http://localhost:8000 (API docs at /docs)
- **Frontend**: http://127.0.0.1:8050

**Option B: Manual Start**

Alternatively, start each component manually:

**Backend:**
```powershell
cd backend
python -m app.main
# Or: .\start_backend.ps1
```
Backend runs at: **http://localhost:8000**

**Frontend** (in a new terminal):
```powershell
# Activate venv if not already active
.\venv\Scripts\activate

cd frontend
python app.py
# Or: .\start_frontend.ps1
```
Frontend runs at: **http://127.0.0.1:8050**

---

## API Reference

### Search Endpoint

**GET** `/api/search`

**Query Parameters:**
- `q` (required): Search query string
- `top_k` (optional): Number of results (default: 10, max: 50)

**Response:**
```json
[
  {
    "episode": "episode_name",
    "excerpt": "relevant text snippet...",
    "score": 0.8734
  }
]
```

**Example:**
```bash
curl "http://localhost:8000/api/search?q=inteligencia%20artificial&top_k=5"
```

---

## Configuration

All configuration settings are centralized in `backend/app/config/settings.py`. This makes it easy to modify the application behavior in one place.

### Key Configuration Options

Edit `backend/app/config/settings.py` to customize:

**Model Settings:**
```python
WHISPER_MODEL = "large-v3"  # Options: base, small, medium, large, large-v2, large-v3
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Or: all-mpnet-base-v2
```

**Transcription Settings:**
```python
CHUNK_SIZE = 750  # Characters per chunk
TRANSCRIPTION_LANGUAGE = "pt"  # Portuguese (or "en", "es", etc.)
```

**Search Settings:**
```python
DEFAULT_TOP_K = 10  # Default number of search results
MAX_TOP_K = 50  # Maximum allowed results
EXCERPT_MAX_LENGTH = 500  # Max characters in result excerpts
```

**API Settings:**
```python
API_HOST = "0.0.0.0"
API_PORT = 8000
```

For more details on code organization, see [ARCHITECTURE.md](backend/ARCHITECTURE.md).

### Legacy Configuration Notes

Previously, settings were hardcoded in individual service files. Now everything is centralized:

**Whisper Model:**
- Default: `large-v3` (most accurate, slowest)
- Alternatives: `base`, `small`, `medium`, `large`, `large-v2`
- Smaller models are faster but less accurate

**Embedding Model:**
- Default: `all-MiniLM-L6-v2` (fast, good quality)
- Alternatives: `all-mpnet-base-v2` (better quality, slower)

**Chunk Size:**
- Default: 750 characters
- Smaller = more precise, larger = more context

**Language:**
- Default: `"pt"` (Portuguese for Nerdcast)
- Change to `"en"` for English or `None` for auto-detection

---

## Re-running Ingestion

The ingestion script is **idempotent**:
- Won't duplicate existing chunks
- Safely updates index when new files are added

To add new podcasts:
1. Add new audio files to `backend/data/podcasts/`
2. Run `python -m scripts.ingest_podcasts` again
3. Restart the backend API

---

## Performance Notes

### GPU Acceleration

For faster transcription, install PyTorch with CUDA:
```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

For FAISS GPU support:
```powershell
pip uninstall faiss-cpu
pip install faiss-gpu
```

### Production Considerations

This is an MVP. For production:
- Use PostgreSQL instead of SQLite
- Add authentication
- Implement caching
- Use FAISS approximate search (IVF, HNSW) for large datasets
- Deploy with Docker
- Add monitoring and logging
- Set proper CORS origins

---

## Troubleshooting

### "FFmpeg not found"
Install FFmpeg (see Prerequisites section)

### "FAISS index not found"
Run the ingestion script first: `python -m scripts.ingest_podcasts`

### "Cannot connect to backend"
Make sure backend is running on port 8000: `python -m app.main`

### Out of memory during transcription
Use a smaller Whisper model or process files one at a time

---

## License

MIT

---

## Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/)
- [Whisper](https://github.com/openai/whisper)
- [sentence-transformers](https://www.sbert.net/)
- [FAISS](https://github.com/facebookresearch/faiss)
- [Dash](https://dash.plotly.com/)
