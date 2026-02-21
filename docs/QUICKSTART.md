# Quick Reference Guide

## Common Commands

### Run Backend API
```powershell
python -m backend.app.main
```

### Run Data Pipelines

**Download episodes:**
```powershell
python -m backend.pipelines.download --limit 10
```

**Transcribe and index:**
```powershell
python -m backend.pipelines.ingest
```

**Rebuild FAISS index:**
```powershell
python -m backend.pipelines.rebuild_index
```

**Database migration:**
```powershell
python -m backend.pipelines.migrate_db
```

**Update metadata:**
```powershell
python -m backend.pipelines.update_metadata
```

### Run Frontend
```powershell
python frontend/app.py
```

### Start Everything (Development)
```powershell
.\infra\start.ps1
```

## Import Patterns

### Logger
```python
from backend.app.core.logger import logger

logger.info("Information message")
logger.success("✓ Success message")
logger.warning("⚠️ Warning message")
logger.error("❌ Error message")
logger.header("SECTION TITLE", width=60)
logger.section("Subsection")
logger.progress(current=5, total=10, item_name="episode_001.mp3")
```

### Configuration
```python
from backend.app.core.config import settings

db_path = settings.get_database_path()
index_path = settings.get_faiss_index_path()
model = settings.WHISPER_MODEL
```

### Database
```python
from backend.app.db.session import get_db_session, init_db
from backend.app.db.models import NerdcastEpisode, NerdcastSegment

# Initialize database (creates tables)
init_db()

# Get session
db = get_db_session()

# Query episodes
episodes = db.query(NerdcastEpisode).filter(
    NerdcastEpisode.status == "downloaded"
).all()

# Query segments
segments = db.query(NerdcastSegment).filter(
    NerdcastSegment.episode_filename == "nerdcast_001.mp3"
).all()
```

### Services
```python
from backend.app.services.search_service import SearchService
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.transcription_service import TranscriptionService

# Search
search_service = SearchService()
results = search_service.search(query="inteligência artificial", top_k=10)

# Embeddings
embedding_service = EmbeddingService()
vectors = embedding_service.generate_embeddings(["texto 1", "texto 2"])

# Transcription
transcription_service = TranscriptionService()
result = transcription_service.transcribe_audio("/path/to/audio.mp3")
```

## Project Structure

```
nerdcastfinder/
├── backend/
│   ├── app/
│   │   ├── core/         # Config & logger
│   │   ├── api/          # FastAPI endpoints
│   │   ├── services/     # Business logic
│   │   ├── db/           # Database models
│   │   └── utils/        # Helpers
│   ├── pipelines/        # Data processing
│   ├── tests/            # Tests
│   └── data/             # Runtime data
├── frontend/             # Dash UI
├── infra/                # Infrastructure
└── docs/                 # Documentation
```

## Environment Variables

The project uses `.env` file for sensitive configuration (optional):

```env
# Database
DATABASE_PATH=backend/data/nerdcasts.db

# API
API_HOST=localhost
API_PORT=8000

# Models
WHISPER_MODEL=medium
EMBEDDING_MODEL=all-mpnet-base-v2
WHISPER_DEVICE=cuda  # or 'cpu'
```

## Troubleshooting

### Import Errors
**Problem:** `ModuleNotFoundError: No module named 'backend'`

**Solution:** Ensure you're running from the project root:
```powershell
cd C:\...\nerdcastfinder\nerdcastfinder\nerdcastfinder
python -m backend.app.main
```

### Database Locked
**Problem:** `database is locked`

**Solution:** Close any DB browser connections, or restart:
```powershell
# Kill Python processes
Stop-Process -Name python -Force

# Restart
python -m backend.app.main
```

### CUDA Out of Memory
**Problem:** `RuntimeError: CUDA out of memory`

**Solution:** Use CPU mode in config:
```python
# In backend/app/core/config.py
WHISPER_DEVICE = "cpu"
```

### FAISS Index Not Found
**Problem:** `FileNotFoundError: FAISS index not found`

**Solution:** Rebuild the index:
```powershell
python -m backend.pipelines.rebuild_index
```

## Development Tips

### Hot Reload Backend
```powershell
uvicorn backend.app.main:app --reload
```

### Clear Python Cache
```powershell
Get-ChildItem -Recurse -Filter "__pycache__" | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force
```

### Check Import Structure
```powershell
python -c "from backend.app.core import logger, settings; print('✓ Imports OK')"
```

### Database Shell
```powershell
sqlite3 backend\data\nerdcasts.db
```

```sql
-- Show all tables
.tables

-- Show episode count
SELECT COUNT(*) FROM nerdcast_episodes;

-- Show recent episodes
SELECT filename, title_original, published_date 
FROM nerdcast_episodes 
ORDER BY published_date DESC 
LIMIT 10;

-- Show segment count
SELECT COUNT(*) FROM nerdcast_segments;

-- Exit
.quit
```

## API Endpoints

**Base URL:** `http://localhost:8000`

### Search
```
GET /api/search?q=<query>&top_k=<number>
```

Example:
```powershell
curl "http://localhost:8000/api/search?q=inteligencia%20artificial&top_k=5"
```

### Get All Episodes
```
GET /api/episodes
```

### Get Episode by Filename
```
GET /api/episodes/{filename}
```

Example:
```powershell
curl "http://localhost:8000/api/episodes/nerdcast_001_test"
```

### API Documentation
```
http://localhost:8000/docs
```

## Testing

### Run Specific Test
```powershell
python -m backend.tests.test_model_config
```

### Check Embeddings
```powershell
python -m backend.tests.check_embedding_dimensions
```

## Performance Tips

1. **Use GPU for transcription** (10x faster):
   ```python
   WHISPER_DEVICE = "cuda"
   ```

2. **Batch embeddings**:
   ```python
   EMBEDDING_BATCH_SIZE = 32
   ```

3. **Use medium Whisper model** (6x faster than large):
   ```python
   WHISPER_MODEL = "medium"
   ```

4. **Limit concurrent downloads**:
   ```python
   DOWNLOAD_MAX_CONCURRENT = 2
   ```

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed architecture overview
- [MIGRATION.md](MIGRATION.md) - Migration guide from old structure
- [README.md](../README.md) - Project overview
