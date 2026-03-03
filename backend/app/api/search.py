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
    author: str | None = None
    program_name: str | None = None
    podcast_source: str | None = None
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


@router.get("/search", response_model=list[SearchResult])
async def search(
    q: str = Query(..., description="Texto a buscar nos episódios", min_length=1),
    top_k: int = Query(
        settings.DEFAULT_TOP_K,
        description="Número de resultados a retornar",
        ge=1,
        le=settings.MAX_TOP_K
    ),
    feed: str = Query(
        None,
        description="Filtrar por feed/fonte do podcast (ex: nerdcast, pelada_na_net)"
    ),
    program: str = Query(
        None,
        description="Filtrar por nome do programa (ex: NerdCast, NerdTech)"
    ),
    min_confidence: float = Query(
        None,
        description="Score mínimo de similaridade (0–1). Se omitido, retorna os top_k mais relevantes.",
        ge=0.0,
        le=1.0
    )
):
    """
    Busca semântica em episódios de podcast.

    Converte a query em um embedding vetorial e usa FAISS para encontrar os
    segmentos de transcrição mais similares. Retorna no máximo um resultado
    por episódio (o segmento de maior score).

    - **q**: Texto da busca (ex: "inteligência artificial", "games indie")
    - **top_k**: Quantos episódios retornar (padrão 10, máximo 50)
    - **feed**: Fonte do podcast (`nerdcast`, `pelada_na_net`, …)
    - **program**: Nome do programa (`NerdCast`, `NerdTech`, …)
    - **min_confidence**: Score mínimo de corte (0–1). Resultados abaixo são descartados.
    """
    logger.info(f"[HANDLER] q={q}, top_k={top_k}, feed={feed}, program={program}, min_confidence={min_confidence}")
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

        # Ensure `author`/`program_name`/`podcast_source` are populated
        # Fallback: read directly from sqlite for any missing metadata (robust against ORM issues)
        try:
            import sqlite3
            from pathlib import Path
            db_path = settings.get_database_path()
            # Annotate results with db path and existence for debugging
            db_exists = db_path.exists()
            conn = None
            if db_exists:
                conn = sqlite3.connect(str(db_path))
                cur = conn.cursor()
                for r in results:
                    # record db path/existence per result
                    r.setdefault('_debug', {})
                    r['_debug']['db_path'] = str(db_path)
                    r['_debug']['db_exists'] = db_exists
                    if r.get('author') is None:
                        ep = r.get('episode')
                        if ep:
                            cur.execute('SELECT program_name, podcast_source FROM podcast_episodes WHERE filename = ?', (ep,))
                            row = cur.fetchone()
                            if row:
                                program_name_val, podcast_source_val = row
                                r['program_name'] = program_name_val
                                r['podcast_source'] = podcast_source_val
                                r['author'] = (program_name_val.strip() if program_name_val and program_name_val.strip() else (podcast_source_val if podcast_source_val else None))
                    # Attach debug info about DB lookup
                    try:
                        ep_dbg = r.get('episode')
                        cur.execute('SELECT filename, program_name, podcast_source FROM podcast_episodes WHERE filename = ?', (ep_dbg,))
                        row_dbg = cur.fetchone()
                        if row_dbg:
                            r['_debug'] = {'db_found': True, 'db_filename': row_dbg[0], 'db_program_name': row_dbg[1], 'db_podcast_source': row_dbg[2]}
                        else:
                            r['_debug'] = {'db_found': False, 'db_filename': None}
                    except Exception:
                        r['_debug'] = {'db_lookup_error': True}
                conn.close()
        except Exception:
            # Non-fatal: proceed with whatever results we have
            pass

        # Return raw dicts so we preserve any dynamically-populated metadata
        # (some Pydantic/FastAPI serialization settings may drop None fields)
        # Ensure author/program_name/podcast_source keys exist for frontend fallback
        for r in results:
            if 'author' not in r:
                r['author'] = None
            if 'program_name' not in r:
                r['program_name'] = None
            if 'podcast_source' not in r:
                r['podcast_source'] = None

        return results
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

