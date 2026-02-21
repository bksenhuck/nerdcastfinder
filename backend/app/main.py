"""
FastAPI main application entry point for Nerdcast Finder
"""
import logging
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.api import search, episodes

# Setup logging
log = logging.getLogger("uvicorn.error")

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    log.info("=" * 60)
    log.info(f"📨 INCOMING REQUEST")
    log.info(f"Method: {request.method}")
    log.info(f"URL: {request.url}")
    log.info(f"Path: {request.url.path}")
    log.info(f"Query: {request.url.query}")
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        log.info(f"✓ Response: {response.status_code}")
        log.info(f"⏱️  Duration: {process_time:.3f}s")
        log.info("=" * 60)
        return response
    except Exception as e:
        log.error(f"❌ Exception in request processing:")
        log.error(f"Type: {type(e).__name__}")
        log.error(f"Message: {str(e)}")
        import traceback
        log.error(f"Traceback:\n{traceback.format_exc()}")
        log.error("=" * 60)
        raise

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
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
    log.info("=" * 60)
    log.info("🚀 Application starting up...")
    log.info("=" * 60)
    
    # Pre-initialize search service to load FAISS index
    from app.api.search import get_search_service
    try:
        log.info("🔧 Pre-loading SearchService...")
        get_search_service()
        log.info("✓ SearchService pre-loaded successfully")
    except Exception as e:
        log.error(f"✗ Failed to pre-load SearchService: {e}")
    
    log.info("=" * 60)
    log.info("✓ Application startup complete")
    log.info("=" * 60)


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
    import uvicorn
    from app.utils.logger import logger
    
    logger.header("NERDCAST FINDER - BACKEND API")
    logger.info(f"Starting server on http://{settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"Documentation: http://{settings.API_HOST}:{settings.API_PORT}/docs")
    
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.API_RELOAD
    )
