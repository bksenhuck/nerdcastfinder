"""
Search API endpoint
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.services.search_service import SearchService

router = APIRouter()


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
                    logger.info("🔧 Initializing SearchService singleton...")
                    cls._instance = SearchService()
                    logger.success("SearchService singleton initialized successfully")
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
    logger.header("🔍 SEARCH REQUEST")
    logger.info(f"Query: '{q}'")
    logger.info(f"Top K: {top_k}")
    
    try:
        logger.info("Getting search service...")
        service = get_search_service()
        
        logger.info(f"Service retrieved. Index loaded: {service.index is not None}")
        
        logger.info("Executing search...")
        results = service.search(query=q, top_k=top_k)
        
        logger.success(f"Search completed successfully - Found {len(results)} results")
        
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
        import traceback
        logger.error(f"Search failed: {str(e)}")
        logger.error(f"Type: {type(e).__name__}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        
        # Mensagem amigável para o usuário, detalhes completos nos logs
        raise HTTPException(
            status_code=500, 
            detail="Infelizmente aconteceu um erro ao processar sua busca. Por favor, tente novamente em alguns instantes."
        )

