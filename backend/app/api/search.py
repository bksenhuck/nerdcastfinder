"""
Search API endpoint
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.core.cache import search_cache
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
    ),
    feed: str = Query(
        None,
        description="Filter by feed/podcast source (optional)"
    ),
    program: str = Query(
        None,
        description="Filter by program name (optional)"
    ),
    min_confidence: float = Query(
        None,
        description="Minimum confidence score (0-1). If not specified, returns top K results. If specified, returns only results above threshold.",
        ge=0.0,
        le=1.0
    )
):
    logger.info(f"[HANDLER] Parâmetros: q={q}, top_k={top_k}, feed={feed}, program={program}, min_confidence={min_confidence}")
    """
    Semantic search for podcast episodes
    
    Args:
        q: Search query string
        top_k: Number of results to return (default: 10)
        feed: Optional filter by podcast source/feed
        program: Optional filter by program name
    
    Returns:
        List of search results with episode name, excerpt, and similarity score
    """
    logger.header("🔍 SEARCH REQUEST")
    logger.info(f"Query: '{q}'")
    logger.info(f"Top K: {top_k}")
    logger.info(f"Feed filter: {feed if feed else 'None'}")
    logger.info(f"Program filter: {program if program else 'None'}")
    logger.info(f"Min Confidence: {min_confidence if min_confidence is not None else 'None (returns top K)'}")
    
    try:
        logger.info("Getting search service...")
        service = get_search_service()
        
        logger.info(f"Service retrieved. Index loaded: {service.index is not None}")
        
        logger.info("Executing search...")
        results = service.search(
            query=q,
            top_k=top_k,
            podcast_source=feed,
            program_name=program,
            min_confidence=min_confidence
        )
        
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


@router.get("/cache/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        Cache stats including hit rate, total entries, TTL, etc.
    """
    logger.header("📊 CACHE STATS REQUEST")
    
    try:
        stats = search_cache.get_stats()
        logger.info(f"Cache stats: {stats}")
        logger.success("Cache stats retrieved successfully")
        return stats
    except Exception as e:
        logger.error(f"Failed to get cache stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao recuperar estatísticas de cache"
        )


@router.post("/cache/clear")
async def clear_cache() -> Dict[str, str]:
    """
    Clear all cache entries.
    
    Returns:
        Confirmation message
    """
    logger.header("🗑️  CACHE CLEAR REQUEST")
    
    try:
        search_cache.clear()
        logger.success("Cache cleared successfully")
        return {"message": "Cache limpo com sucesso", "status": "success"}
    except Exception as e:
        logger.error(f"Failed to clear cache: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao limpar cache"
        )


@router.post("/cache/reset-stats")
async def reset_cache_stats() -> Dict[str, str]:
    """
    Reset cache statistics (hit/miss counts).
    
    Returns:
        Confirmation message
    """
    logger.header("🔄 CACHE STATS RESET REQUEST")
    
    try:
        search_cache.reset_stats()
        logger.success("Cache stats reset successfully")
        return {"message": "Estatísticas de cache resetadas", "status": "success"}
    except Exception as e:
        logger.error(f"Failed to reset cache stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao resetar estatísticas de cache"
        )

