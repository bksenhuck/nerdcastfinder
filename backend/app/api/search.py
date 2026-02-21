"""
Search API endpoint
"""
import logging
from fastapi import APIRouter, Query, HTTPException
from typing import List
from pydantic import BaseModel

from app.config.settings import settings
from app.services.search_service import SearchService
from app.utils.logger import logger

router = APIRouter()

# Setup logging for uvicorn
log = logging.getLogger("uvicorn.error")


class SearchResult(BaseModel):
    episode: str
    title: str
    image_url: str | None = None
    published_date: str | None = None
    duration_seconds: int | None = None
    file_size_mb: float | None = None
    excerpt: str
    score: float


class SearchServiceSingleton:
    """Thread-safe singleton for SearchService"""
    _instance = None
    _lock = None
    
    def __new__(cls):
        if cls._lock is None:
            import threading
            cls._lock = threading.Lock()
        
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    log.info("🔧 Initializing SearchService singleton...")
                    logger.info("Initializing SearchService singleton...")
                    cls._instance = SearchService()
                    log.info("✓ SearchService singleton initialized successfully")
        return cls._instance


def get_search_service() -> SearchService:
    """Get the singleton search service instance"""
    return SearchServiceSingleton()


@router.get("/search", response_model=List[SearchResult])
async def search(
    q: str = Query(..., description="Search query", min_length=1),
    top_k: int = Query(
        settings.DEFAULT_TOP_K,
        description="Number of results to return",
        ge=1,
        le=settings.MAX_TOP_K
    )
):
    """
    Semantic search for podcast episodes
    
    Args:
        q: Search query string
        top_k: Number of results to return (default: 10)
    
    Returns:
        List of search results with episode name, excerpt, and similarity score
    """
    # Force print to console
    print("\n" + "=" * 60)
    print("🔍 SEARCH ENDPOINT CALLED!")
    print("=" * 60)
    print(f"Query: '{q}'")
    print(f"Top K: {top_k}")
    print("=" * 60)
    
    log.info("=" * 60)
    log.info(f"🔍 SEARCH REQUEST")
    log.info("=" * 60)
    log.info(f"Query: '{q}'")
    log.info(f"Top K: {top_k}")
    
    try:
        log.info("Getting search service...")
        print("Getting search service...")
        service = get_search_service()
        
        log.info(f"Service retrieved. Index loaded: {service.index is not None}")
        print(f"Service retrieved. Index loaded: {service.index is not None}")
        
        log.info("Executing search...")
        print("Executing search...")
        results = service.search(query=q, top_k=top_k)
        
        log.info(f"✓ Search completed successfully")
        log.info(f"✓ Found {len(results)} results")
        log.info("=" * 60)
        print(f"✓ Found {len(results)} results")
        print("=" * 60 + "\n")
        
        return [
            SearchResult(
                episode=result["episode"],
                title=result.get("title", result["episode"]),
                image_url=result.get("image_url"),
                published_date=result.get("published_date"),
                duration_seconds=result.get("duration_seconds"),
                file_size_mb=result.get("file_size_mb"),
                excerpt=result["excerpt"],
                score=result["score"]
            )
            for result in results
        ]
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ SEARCH ERROR!")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print(f"Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        print("=" * 60 + "\n")
        
        log.error("=" * 60)
        log.error(f"✗ SEARCH FAILED")
        log.error("=" * 60)
        log.error(f"Error: {str(e)}")
        log.error(f"Type: {type(e).__name__}")
        import traceback
        log.error(f"Traceback:\n{traceback.format_exc()}")
        log.error("=" * 60)
        
        # Mensagem amigável para o usuário, detalhes completos nos logs
        raise HTTPException(
            status_code=500, 
            detail="Infelizmente aconteceu um erro ao processar sua busca. Por favor, tente novamente em alguns instantes."
        )

