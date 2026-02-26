# Architecture Overview

## Project Structure

```
nerdcastfinder/
├── backend/               # Backend package (FastAPI + data pipelines)
│   ├── __init__.py
│   ├── app/              # FastAPI application
│   │   ├── __init__.py
│   │   ├── main.py       # FastAPI entry point
│   │   ├── core/         # Core configuration and utilities
│   │   │   ├── __init__.py
│   │   │   ├── config.py # Centralized settings
│   │   │   └── logger.py # Colorized logging
│   │   ├── api/          # API endpoints
│   │   │   ├── search.py
│   │   │   └── episodes.py
│   │   ├── services/     # Business logic
│   │   │   ├── search_service.py
│   │   │   ├── embedding_service.py
│   │   │   └── transcription_service.py
│   │   ├── db/           # Database models and sessions
│   │   │   ├── models.py
│   │   │   └── session.py
│   │   └── utils/        # Helper utilities
│   │       ├── text_utils.py
│   │       └── file_utils.py
│   ├── pipelines/        # Data ingestion and processing jobs
│   │   ├── __init__.py
│   │   ├── download.py       # Download podcast episodes
│   │   ├── ingest.py         # Transcribe and index episodes
│   │   ├── rebuild_index.py  # Rebuild FAISS index
│   │   ├── migrate_db.py     # Database migrations
│   │   └── update_metadata.py # Update episode metadata
│   ├── tests/            # Backend tests
│   │   ├── __init__.py
│   │   ├── test_model_config.py
│   │   └── check_embedding_dimensions.py
│   └── data/             # Runtime data (SQLite, FAISS index, podcasts)
│       ├── podcast_database.db
│       ├── faiss_index/
│       └── podcasts/
├── frontend/             # Dash frontend application
│   ├── app.py
│   ├── assets/
│   │   └── theme.css
│   └── pages/
│       ├── home.py
│       └── about.py
├── infra/                # Infrastructure scripts
│   └── start.ps1         # Development startup script
└── docs/                 # Documentation
    ├── ARCHITECTURE.md   # This file
    └── MIGRATION.md      # Migration guide
```

## Design Principles

### 1. Separation of Concerns

- **Backend API** (`backend/app/`): Serves HTTP requests via FastAPI
- **Data Pipelines** (`backend/pipelines/`): Batch processing jobs (ETL)
- **Frontend** (`frontend/`): User interface with Dash

### 2. Clean Imports

All imports use **absolute paths** from the project root:

```python
# ✅ Correct
from backend.app.core.logger import logger
from backend.app.core.config import settings
from backend.app.services.search_service import SearchService

# ❌ Avoid
from app.core.logger import logger  # Relative to backend
from utils.logger import logger     # Ambiguous path
```

### 3. Centralized Configuration

All configuration is in `backend/app/core/config.py`:
- Model settings (Whisper, embeddings)
- Database paths
- API settings
- Pipeline parameters

### 4. Proper Python Packages

Every directory with Python code has an `__init__.py` file, making imports predictable and allowing package-level exports.

## Running the Application

### Start the Backend API

```powershell
# Run backend API
python -m backend.app.main
```

Or using uvicorn directly:
```powershell
cd backend
uvicorn app.main:app --reload
```

### Run Data Pipelines

```powershell
# Download episodes
python -m backend.pipelines.download --limit 10

# Transcribe and index
python -m backend.pipelines.ingest

# Rebuild FAISS index
python -m backend.pipelines.rebuild_index

# Database migrations
python -m backend.pipelines.migrate_db

# Update metadata
python -m backend.pipelines.update_metadata
```

### Start the Frontend

```powershell
python frontend/app.py
```

### Start Everything (Development)

```powershell
.\infra\start.ps1
```

## Key Components

### Core (`backend/app/core/`)

- **logger.py**: Colorized console logging with timestamps
  - `logger.info()`, `logger.success()`, `logger.warning()`, `logger.error()`
  - `logger.header()`, `logger.section()`, `logger.progress()`

- **config.py**: Centralized configuration
  - Model settings (Whisper, embeddings)
  - Database paths
  - API configuration

### Services (`backend/app/services/`)

- **SearchService**: FAISS-based semantic search
- **EmbeddingService**: Sentence transformer embeddings
- **TranscriptionService**: Whisper transcription

### Pipelines (`backend/pipelines/`)

All pipelines are runnable as modules:

1. **download.py**: Fetches RSS feed and downloads MP3 files
2. **ingest.py**: Transcribes audio and creates embeddings
3. **rebuild_index.py**: Rebuilds FAISS index from database
4. **migrate_db.py**: Database schema migrations
5. **update_metadata.py**: Updates episode metadata from RSS

## Database Schema

### nerdcast_episodes

- `filename` (PK): Normalized episode name
- `title_original`: Original title from RSS
- `published_date`: Episode publication date
- `duration_seconds`: Audio duration
- `file_size_mb`: File size
- `image_url`: Episode cover image
- `summary`: Episode description
- `status`: download/transcribed/indexed
- `downloaded_at`: Download timestamp

### nerdcast_segments

- `id` (PK): Auto-increment
- `episode_filename` (FK): Links to episodes
- `chunk_index`: Segment order
- `text`: Transcribed text
- `embedding`: 768-dim vector (binary)
- `start_time`: Segment start (seconds)
- `end_time`: Segment end (seconds)

## Technology Stack

### Backend
- **FastAPI**: REST API framework
- **SQLite**: Episode and segment storage
- **SQLAlchemy**: ORM
- **FAISS**: Vector similarity search
- **Whisper**: Audio transcription
- **Sentence Transformers**: Text embeddings

### Frontend
- **Dash**: Interactive web UI
- **Plotly**: Visualization
- **Bootstrap**: Styling

### ML/AI
- **all-mpnet-base-v2**: 768-dim embeddings (best quality)
- **Whisper Medium**: Fast Portuguese transcription
- **PyTorch**: ML framework with CUDA support

## Development Workflow

1. **Download episodes**: `python -m backend.pipelines.download --limit 5`
2. **Transcribe and index**: `python -m backend.pipelines.ingest`
3. **Start backend**: `python -m backend.app.main`
4. **Start frontend**: `python frontend/app.py`
5. **Search**: Navigate to http://localhost:8050

## Best Practices

### Logging

Always use the centralized logger:

```python
from backend.app.core.logger import logger

logger.info("Processing started")
logger.success("✓ Task completed")
logger.warning("⚠️ Low disk space")
logger.error("❌ Failed to connect")
logger.section("Data Loading")
logger.header("PIPELINE STARTED")
```

### Configuration

Never hardcode paths or settings:

```python
from backend.app.core.config import settings

db_path = settings.get_database_path()
model_name = settings.WHISPER_MODEL
```

### Database Sessions

Always use session management:

```python
from backend.app.db.session import get_db_session

db = get_db_session()
episodes = db.query(NerdcastEpisode).all()
```

### Service Initialization

Services should be initialized once and reused:

```python
from backend.app.services.search_service import SearchService

search_service = SearchService()  # Singleton pattern
results = search_service.search("query", top_k=10)
```

## Future Improvements

- [ ] Add pytest integration for testing
- [ ] Implement CI/CD pipeline
- [ ] Add Docker containerization
- [ ] Implement Alembic for database migrations
- [ ] Add API authentication
- [ ] Implement caching layer (Redis)
- [ ] Add monitoring and observability
- [ ] Implement async transcription with Celery
