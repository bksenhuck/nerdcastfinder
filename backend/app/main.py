"""
FastAPI main application entry point for Nerdcast Finder
"""
import logging
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.api import search, episodes
from backend.app.core.logger import logger

# Increase default python logging level (configurable via LOG_LEVEL env var)
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.header("Incoming HTTP Request")
    logger.info(f"Method: {request.method}")
    logger.info(f"URL: {request.url}")
    logger.info(f"Path: {request.url.path}")
    logger.info(f"Query: {request.url.query}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"✓ Response: {response.status_code}")
        logger.info(f"⏱️  Duration: {process_time:.3f}s")
        logger.info("=" * 60)
        return response
    except Exception as e:
        logger.error(f"❌ Exception in request processing:")
        logger.error(f"Type: {type(e).__name__}")
        logger.error(f"Message: {str(e)}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        logger.error("=" * 60)
        raise

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Include routers
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(episodes.router, prefix="/api", tags=["episodes"])


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
