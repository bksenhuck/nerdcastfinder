# Migration Guide: Old → New Structure

This document tracks all file movements and import changes from the refactoring.

## Summary of Changes

**Goal**: Restructure the project into a clean, production-ready architecture with proper Python packaging, separated concerns, and absolute imports.

## Directory Structure Changes

### Created Directories

```
backend/app/core/          ← NEW: Core configuration and utilities
backend/pipelines/         ← NEW: Data processing pipelines
docs/                      ← NEW: Project documentation
infra/                     ← NEW: Infrastructure scripts
```

### Removed Directories

```
utils/                     ← REMOVED: Moved to backend/app/core/
scripts/                   ← REMOVED: Moved to backend/pipelines/
tests/                     ← REMOVED: Moved to backend/tests/
backend/scripts/           ← REMOVED: Moved to backend/pipelines/
backend/app/config/        ← REMOVED: Moved to backend/app/core/
```

## File Movement Map

### Configuration & Utilities

| Old Path | New Path | Notes |
|----------|----------|-------|
| `utils/logger.py` | `backend/app/core/logger.py` | Centralized colorized logger |
| `backend/app/config/settings.py` | `backend/app/core/config.py` | Centralized configuration |

### Data Pipelines

| Old Path | New Path | Notes |
|----------|----------|-------|
| `backend/scripts/download_podcasts.py` | `backend/pipelines/download.py` | Episode downloader |
| `backend/scripts/ingest_podcasts.py` | `backend/pipelines/ingest.py` | Transcription & indexing |
| `backend/scripts/rebuild_faiss_index.py` | `backend/pipelines/rebuild_index.py` | Index rebuilder |
| `scripts/migrate_db.py` | `backend/pipelines/migrate_db.py` | Database migrations |
| `scripts/update_missing_metadata.py` | `backend/pipelines/update_metadata.py` | Metadata updater |

### Tests

| Old Path | New Path | Notes |
|----------|----------|-------|
| `tests/test_model_config.py` | `backend/tests/test_model_config.py` | Model configuration tests |
| `tests/check_embedding_dimensions.py` | `backend/tests/check_embedding_dimensions.py` | Embedding validation |

### Infrastructure

| Old Path | New Path | Notes |
|----------|----------|-------|
| `start.ps1` | `infra/start.ps1` | Development startup script |

## Import Changes

All imports now use **absolute paths** from the project root.

### Configuration Imports

```python
# Old
from app.config.settings import settings
from utils.logger import logger

# New
from backend.app.core.config import settings
from backend.app.core.logger import logger
```

### Database Imports

```python
# Old
from app.db.models import NerdcastEpisode, NerdcastSegment
from app.db.session import get_db_session, init_db

# New
from backend.app.db.models import NerdcastEpisode, NerdcastSegment
from backend.app.db.session import get_db_session, init_db
```

### Service Imports

```python
# Old
from app.services.search_service import SearchService
from app.services.embedding_service import EmbeddingService
from app.services.transcription_service import TranscriptionService

# New
from backend.app.services.search_service import SearchService
from backend.app.services.embedding_service import EmbeddingService
from backend.app.services.transcription_service import TranscriptionService
```

### API Imports

```python
# Old
from app.api import search, episodes

# New
from backend.app.api import search, episodes
```

### Utility Imports

```python
# Old
from app.utils.text_utils import truncate_text
from app.utils.file_utils import find_audio_files

# New
from backend.app.utils.text_utils import truncate_text
from backend.app.utils.file_utils import find_audio_files
```

### Pipeline Imports

```python
# Old
from backend.scripts.rebuild_faiss_index import rebuild_faiss_index

# New
from backend.pipelines.rebuild_index import rebuild_faiss_index
```

## Removed Code

### Path Manipulation

All `sys.path.insert()` hacks have been removed. The project now uses proper Python packaging with `__init__.py` files.

#### Before:
```python
import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config.settings import settings
```

#### After:
```python
from backend.app.core.config import settings
```

## New `__init__.py` Files

Added package initializers:

```
backend/__init__.py
backend/app/__init__.py
backend/app/core/__init__.py
backend/pipelines/__init__.py
backend/tests/__init__.py
```

### Core Package Exports

`backend/app/core/__init__.py` exports commonly used items:
```python
from backend.app.core.logger import logger
from backend.app.core.config import settings

__all__ = ["logger", "settings"]
```

## Running Commands (Old → New)

### Backend API

```powershell
# Old
cd backend
python -m app.main

# New
python -m backend.app.main
```

### Pipelines

```powershell
# Old
python -m scripts.download_podcasts --limit 10
python -m backend.scripts.ingest_podcasts
python -m backend.scripts.rebuild_faiss_index

# New
python -m backend.pipelines.download --limit 10
python -m backend.pipelines.ingest
python -m backend.pipelines.rebuild_index
```

### Tests

```powershell
# Old
python tests/test_model_config.py

# New
python -m backend.tests.test_model_config
```

### Infrastructure

```powershell
# Old
.\start.ps1

# New
.\infra\start.ps1
```

## Files Modified (Import Updates)

All imports were updated in the following files:

### Backend App
- `backend/app/main.py`
- `backend/app/api/search.py`
- `backend/app/api/episodes.py`
- `backend/app/db/session.py`
- `backend/app/services/search_service.py`
- `backend/app/services/embedding_service.py`
- `backend/app/services/transcription_service.py`

### Pipelines
- `backend/pipelines/download.py`
- `backend/pipelines/ingest.py`
- `backend/pipelines/rebuild_index.py`
- `backend/pipelines/migrate_db.py`
- `backend/pipelines/update_metadata.py`

### Tests
- `backend/tests/test_model_config.py`
- `backend/tests/check_embedding_dimensions.py`

## Breaking Changes

### 1. Command-Line Invocation

All pipeline scripts must now be run as modules with the new paths:

```powershell
# ❌ Old (will fail)
python -m scripts.download_podcasts

# ✅ New
python -m backend.pipelines.download
```

### 2. Import Paths in Custom Scripts

If you have any custom scripts importing from the backend, update them:

```python
# ❌ Old
from app.config.settings import settings

# ✅ New
from backend.app.core.config import settings
```

### 3. Working Directory

The project must be run from the root directory (where `backend/` and `frontend/` are located).

```powershell
# Correct location
C:\...\nerdcastfinder\nerdcastfinder\nerdcastfinder> python -m backend.app.main
```

### 4. Start Script Location

The startup script has moved:

```powershell
# ❌ Old
.\start.ps1

# ✅ New
.\infra\start.ps1
```

## Migration Checklist

If you have local changes or custom scripts, follow this checklist:

- [ ] Update all imports from `app.*` to `backend.app.*`
- [ ] Update all imports from `utils.logger` to `backend.app.core.logger`
- [ ] Update all imports from `app.config.settings` to `backend.app.core.config`
- [ ] Remove any `sys.path.insert()` hacks
- [ ] Update script invocation commands to new module paths
- [ ] Update working directory to project root
- [ ] Test that all pipelines run correctly
- [ ] Test that backend API starts without errors
- [ ] Test that frontend connects to backend successfully

## Benefits of New Structure

✅ **Clear separation of concerns**: API vs. pipelines vs. frontend  
✅ **Proper Python packaging**: No more path manipulation  
✅ **Absolute imports**: Unambiguous and IDE-friendly  
✅ **Centralized configuration**: Single source of truth  
✅ **Organized infrastructure**: Scripts in dedicated folder  
✅ **Better testability**: Tests alongside the code they test  
✅ **Production-ready**: Follows Python best practices  
✅ **Easier onboarding**: Clear structure for new developers  

## Support

If you encounter any issues after migration:

1. Ensure you're in the project root directory
2. Check that all `__init__.py` files are present
3. Verify imports use absolute paths (`backend.app.*`)
4. Clear any Python cache: `Remove-Item -Recurse -Force **\__pycache__`
5. Restart your IDE to refresh import resolution

## Rollback (Emergency Only)

If critical issues arise, the old structure is preserved in git history:

```powershell
git log --oneline  # Find commit before refactor
git checkout <commit-hash>
```

However, the new structure is recommended for long-term maintainability.
