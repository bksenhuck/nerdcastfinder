# 🚀 Quick Start

## Installation

First, install all dependencies using the automated script:

### Windows

```powershell
# PowerShell (recommended)
.\install.ps1

# Command Prompt / Batch
.\install.bat
```

### Linux / macOS

```bash
# Make executable (first time only)
chmod +x install.sh

# Run
./install.sh
```

This will automatically install all backend and frontend dependencies.

---

## Start the Application

After installing dependencies, use one of these scripts to start both backend and frontend:

### Windows

```powershell
# PowerShell (recommended)
.\start.ps1

# Command Prompt / Batch
.\start.bat
```

### Linux / macOS

```bash
# Make executable (first time only)
chmod +x start.sh

# Run
./start.sh
```

## What it does

✅ Opens **two terminal windows**:
1. **Backend API** - http://localhost:8000
2. **Frontend UI** - http://127.0.0.1:8050

The backend API documentation is available at http://localhost:8000/docs

---

## First Time Setup

Before running the start script:

1. **Install dependencies** (see main [README.md](README.md))
2. **Add podcast audio files** to `backend/data/podcasts/`
3. **Run ingestion** to build the search index:
   ```powershell
   cd backend
   python -m scripts.ingest_podcasts
   ```

---

## Individual Scripts

If you prefer to start each component separately:

- **Backend only**: `backend/start_backend.ps1`
- **Frontend only**: `frontend/start_frontend.ps1`

---

For full documentation, see [README.md](README.md)
