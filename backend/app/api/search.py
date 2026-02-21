"""
Search API endpoint
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List
from pydantic import BaseModel

from app.config.settings import settings
from app.services.search_service import SearchService

router = APIRouter()

# Initialize search service (singleton)
search_service = None


class SearchResult(BaseModel):
    episode: str
    excerpt: str
    score: float


def get_search_service() -> SearchService:
    """Lazy load the search service"""
    global search_service
    if search_service is None:
        search_service = SearchService()
    return search_service


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
    try:
        service = get_search_service()
        results = service.search(query=q, top_k=top_k)
        
        return [
            SearchResult(
                episode=result["episode"],
                excerpt=result["excerpt"],
                score=result["score"]
            )
            for result in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
