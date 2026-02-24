"""
FastAPI main application entry point for Nerdcast Finder
"""
from backend.app.core.logger import logger
logger.header("[BOOT] Iniciando backend/main.py", width=60)
import logging
import time
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.wsgi import WSGIMiddleware
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os
import subprocess
import shutil
from fastapi.responses import JSONResponse

from backend.app.core.config import settings
from backend.app.api import search, episodes

from backend.app.core.logger import logger

# Dash integration (import frontend.app explicitly to avoid module name conflict)
import importlib
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))


logger.info("[BOOT] Criando FastAPI app...")
app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION
)
logger.info("[BOOT] FastAPI app criado.")

# Track whether UI was mounted so root can redirect to it when available.
UI_MOUNTED = False

# Try to import and mount the Dash frontend if Dash is available. On
# environments where the frontend dependencies are not installed (e.g.
# a backend-only deploy), avoid crashing the process and continue
# Search readiness flags. `search_ready` is True only after FAISS index
# and mapping were successfully loaded. `search_loading` indicates an
# in-progress background load. These are safe globals per worker.
search_ready = False
search_loading = False
search_load_started_at = None
search_load_duration = None
# serving the API.
try:
    logger.info("[BOOT] Tentando importar o frontend (Dash)...")
    dash_app_module = importlib.import_module("frontend.app")
    # Only mount if the module exposes the Dash server object
    if hasattr(dash_app_module, "app") and hasattr(dash_app_module.app, "server"):
        logger.info("[BOOT] Montando Dash app em /ui...")
        app.mount("/ui", WSGIMiddleware(dash_app_module.app.server))
        UI_MOUNTED = True
        logger.info("[BOOT] Dash app montado em /ui.")
    else:
        logger.warning("[BOOT] Módulo frontend carregado mas não expõe 'app.server'; pulando montagem.")
except ModuleNotFoundError as e:
    logger.warning("[BOOT] Dash não está instalado no ambiente; UI não será montada.\n"
                   "Install 'dash' and related packages to enable the UI.")
except Exception as e:
    logger.error(f"[BOOT] Erro ao tentar montar frontend: {e}")


# Middleware de log detalhado
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.header("[MIDDLEWARE] Nova requisição HTTP", width=60)
    logger.info(f"[MIDDLEWARE] Method: {request.method}")
    logger.info(f"[MIDDLEWARE] URL: {request.url}")
    logger.info(f"[MIDDLEWARE] Path: {request.url.path}")
    logger.info(f"[MIDDLEWARE] Query: {request.url.query}")
    start_time = time.time()
    try:
        logger.info("[MIDDLEWARE] Chamando próximo handler...")
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"[MIDDLEWARE] ✓ Response: {response.status_code}")
        logger.info(f"[MIDDLEWARE] ⏱️  Duration: {process_time:.3f}s")
        logger.info("[MIDDLEWARE] Fim da requisição.")
        logger.info("=" * 60)
        return response
    except Exception as e:
        logger.error(f"[MIDDLEWARE] ❌ Exception in request processing:")
        logger.error(f"[MIDDLEWARE] Type: {type(e).__name__}")
        logger.error(f"[MIDDLEWARE] Message: {str(e)}")
        import traceback
        logger.error(f"[MIDDLEWARE] Traceback:\n{traceback.format_exc()}")
        logger.error("[MIDDLEWARE] =" * 60)
        raise

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

logger.info("[BOOT] Incluindo routers de API...")
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(episodes.router, prefix="/api", tags=["episodes"])
logger.info("[BOOT] Routers incluídos.")


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup without blocking the event loop.

    Spawns a background task that will load the FAISS index so the
    worker can begin accepting connections sooner. Heavy operations
    are executed in a thread executor inside the background task.
    """
    logger.header("Application Startup", width=60)
    
    try:
        logger.info("🔧 Spawning background FAISS index loader...")
        asyncio.create_task(load_index_background())
        logger.info("✓ Background FAISS loader spawned")
    except Exception as e:
        logger.error(f"✗ Failed to spawn background loader: {e}")
    
    logger.info("✓ Application startup complete")
    logger.info("=" * 60)


async def load_index_background():
    """Background task: run blocking index initialization in executor.

    - Calls `get_search_service()` inside a thread executor to avoid
      blocking the event loop.
    - Attempts optional GCS download if `FAISS_GCS_URI` or
      `FAISS_MAPPING_GCS_URI` are provided via environment variables.
    - Sets `search_ready` to True on success and logs duration.
    """
    global search_ready, search_loading, search_load_started_at, search_load_duration

    if search_ready:
        logger.info("[BOOT] SearchService already marked ready; skipping load.")
        return

    if search_loading:
        logger.info("[BOOT] SearchService load already in progress; skipping duplicate start.")
        return

    search_loading = True
    search_load_started_at = time.time()
    logger.info("[BOOT] Background FAISS load: starting...")

    # Optional: try to download index/mapping from GCS if env vars are set
    faiss_gcs_uri = os.environ.get("FAISS_GCS_URI")
    mapping_gcs_uri = os.environ.get("FAISS_MAPPING_GCS_URI")
    try:
        target_dir = settings.get_faiss_dir()
        # If target_dir is not writable inside the container, use /tmp/faiss
        if not os.access(str(target_dir), os.W_OK):
            target_dir = Path("/tmp/faiss")
            target_dir.mkdir(parents=True, exist_ok=True)

        idx_path = settings.get_faiss_index_path()
        if faiss_gcs_uri and not Path(idx_path).exists():
            logger.info(f"[BOOT] FAISS index missing locally — attempting GCS download: {faiss_gcs_uri}")
            try:
                dest = target_dir / Path(str(idx_path)).name
                subprocess.run(["gsutil", "cp", faiss_gcs_uri, str(dest)], check=True)
                os.environ["FAISS_INDEX_PATH"] = str(dest)
                logger.info(f"[BOOT] FAISS index downloaded to {dest}")
            except FileNotFoundError:
                logger.error("[BOOT] gsutil not found in the image; cannot download FAISS index.\n"
                             "Install gcloud SDK or provide the index in the image or via another mechanism.")
            except subprocess.CalledProcessError as cpe:
                logger.error(f"[BOOT] gsutil failed to download FAISS index: {cpe}")

        mapping_path = settings.get_faiss_dir() / "embedding_id_mapping.npy"
        if mapping_gcs_uri and not mapping_path.exists():
            logger.info(f"[BOOT] embedding_id_mapping missing locally — attempting GCS download: {mapping_gcs_uri}")
            try:
                dest_map = mapping_path
                subprocess.run(["gsutil", "cp", mapping_gcs_uri, str(dest_map)], check=True)
                logger.info(f"[BOOT] mapping file downloaded to {dest_map}")
            except FileNotFoundError:
                logger.error("[BOOT] gsutil not found in the image; cannot download mapping file.")
            except subprocess.CalledProcessError as cpe:
                logger.error(f"[BOOT] gsutil failed to download mapping file: {cpe}")
    except Exception:
        # Non-fatal: if download logic fails, we'll still attempt to load
        # the index and let SearchService handle missing files.
        logger.exception("[BOOT] Unexpected error during optional GCS download step")

    loop = asyncio.get_event_loop()
    try:
        from backend.app.api.search import get_search_service

        await loop.run_in_executor(None, get_search_service)

        search_ready = True
        search_load_duration = time.time() - search_load_started_at
        logger.info(f"[BOOT] Background FAISS load completed in {search_load_duration:.2f}s")
    except Exception as exc:  # noqa: BLE001 - keep broad for robustness here
        logger.error(f"[BOOT] Background FAISS load failed: {exc}")
    finally:
        search_loading = False


@app.get("/ready")
async def ready():
    """Readiness endpoint — returns 200 only when search index is ready.

    - 200 + {"status": "ready"} when `search_ready` is True
    - 503 + {"status": "loading"} otherwise
    """
    if search_ready:
        return JSONResponse(status_code=200, content={"status": "ready"})
    return JSONResponse(status_code=503, content={"status": "loading"})


@app.get("/favicon.ico")
async def favicon():
    """Serve a favicon to avoid 500s when browsers request it.

    Looks for `frontend/assets/images/podcast_finder_logo.png` relative to
    the repository and returns it as a `FileResponse`. If the file is not
    present, returns 204 No Content.
    """
    try:
        # repo_root/backend/app/main.py -> go up three to repo root
        repo_root = Path(__file__).resolve().parents[2]
        candidate = repo_root / "frontend" / "assets" / "images" / "podcast_finder_logo.png"
        if candidate.exists():
            return FileResponse(str(candidate), media_type="image/png")
    except Exception:
        pass
    return Response(status_code=204)


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import os
    import uvicorn

    logger.header("NERDCAST FINDER - BACKEND API")
    # Respect PORT env var when running as script (Render provides $PORT)
    port = int(os.environ.get("PORT", settings.API_PORT))
    logger.info(f"Starting server on http://{settings.API_HOST}:{port}")
    logger.info(f"Documentation: http://{settings.API_HOST}:{port}/docs")

    uvicorn.run(
        "backend.app.main:app",
        host=settings.API_HOST,
        port=port,
        reload=False,
        log_level=settings.LOG_LEVEL.lower() if hasattr(settings, 'LOG_LEVEL') else "info"
    )
