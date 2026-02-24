"""
FastAPI main application entry point for Nerdcast Finder
"""
from backend.app.core.logger import logger
logger.header("[BOOT] Iniciando backend/main.py", width=60)
import logging
import time
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse
from fastapi.middleware.wsgi import WSGIMiddleware
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware

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

# Try to import and mount the Dash frontend if Dash is available. On
# environments where the frontend dependencies are not installed (e.g.
# a backend-only deploy), avoid crashing the process and continue
# serving the API.
try:
    logger.info("[BOOT] Tentando importar o frontend (Dash)...")
    dash_app_module = importlib.import_module("frontend.app")
    # Only mount if the module exposes the Dash server object
    if hasattr(dash_app_module, "app") and hasattr(dash_app_module.app, "server"):
        logger.info("[BOOT] Montando Dash app em /ui...")
        app.mount("/ui", WSGIMiddleware(dash_app_module.app.server))
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
    """Initialize services on startup"""
    logger.header("Application Startup", width=60)
    
    # Pre-initialize search service to load FAISS index
    from backend.app.api.search import get_search_service
    try:
        logger.info("🔧 Pre-loading SearchService...")
        get_search_service()
        logger.info("✓ SearchService pre-loaded successfully")
    except Exception as e:
        logger.error(f"✗ Failed to pre-load SearchService: {e}")
    
    logger.info("✓ Application startup complete")
    logger.info("=" * 60)


@app.get("/")
async def root():
    return {
        "message": "Nerdcast Finder API",
        "docs": "/docs"
    }


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
