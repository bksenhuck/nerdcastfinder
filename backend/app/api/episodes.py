"""
Episodes API endpoints
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.db.session import get_db_session
from backend.app.db.models import PodcastEpisode

router = APIRouter()


class EpisodeMetadata(BaseModel):
    """Episode metadata response model"""
    filename: str  # Normalized filename (unique key)
    title_original: str  # Original title from RSS
    published_date: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    file_size_mb: Optional[float] = None
    status: str  # downloaded, transcribed, indexed
    
    class Config:
        from_attributes = True


@router.get("/episodes", response_model=List[EpisodeMetadata], tags=["episodes"])
def get_episodes(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    skip: int = Query(0, ge=0, description="Skip N results"),
):
    """
    Get episode metadata
    
    Query Parameters:
    - status: Filter by 'downloaded', 'transcribed', or 'indexed' (optional)
    - limit: Maximum results (default: 100, max: 1000)
    - skip: Skip N results for pagination (default: 0)
    """
    try:
        db = get_db_session()
        
        logger.info("=" * 60)
        logger.info("📺 FETCHING EPISODE METADATA")
        logger.info("=" * 60)
        
        query = db.query(PodcastEpisode)
        
        if status:
            query = query.filter(PodcastEpisode.status == status)
            logger.info(f"Filter: status={status}")
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        episodes = query.order_by(
            PodcastEpisode.published_date.desc()
        ).offset(skip).limit(limit).all()
        
        logger.info(f"✓ Found {len(episodes)} episodes (total: {total})")
        logger.info(f"  Skip: {skip}, Limit: {limit}")
        logger.info("=" * 60)
        
        db.close()
        
        return episodes
    
    except Exception as e:
        logger.error(f"Failed to fetch episodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episodes/{filename}", response_model=EpisodeMetadata, tags=["episodes"])
def get_episode_by_filename(filename: str):
    """
    Get episode metadata by normalized filename
    
    Args:
        filename: Normalized filename (unique key)
    """
    try:
        db = get_db_session()
        
        logger.info("=" * 60)
        logger.info(f"📺 FETCHING EPISODE: {filename}")
        logger.info("=" * 60)
        
        episode = db.query(NerdcastEpisode).filter(
            NerdcastEpisode.filename == filename
        ).first()
        
        db.close()
        
        if not episode:
            logger.error(f"Episode not found: {filename}")
            raise HTTPException(status_code=404, detail="Episode not found")
        
        logger.info(f"✓ Found episode: {episode.title_original}")
        logger.info(f"  Size: {episode.file_size_mb}MB")
        logger.info(f"  Duration: {episode.duration_seconds}s")
        logger.info("=" * 60)
        
        return episode
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch episode {filename}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/episodes/stats/summary", tags=["episodes"])
def get_episodes_stats():
    """
    Get summary statistics about episodes
    """
    try:
        db = get_db_session()
        
        logger.info("=" * 60)
        logger.info("📊 EPISODE STATISTICS")
        logger.info("=" * 60)
        
        total_episodes = db.query(NerdcastEpisode).count()
        downloaded = db.query(NerdcastEpisode).filter(
            NerdcastEpisode.status == "downloaded"
        ).count()
        transcribed = db.query(NerdcastEpisode).filter(
            NerdcastEpisode.status == "transcribed"
        ).count()
        indexed = db.query(NerdcastEpisode).filter(
            NerdcastEpisode.status == "indexed"
        ).count()
        
        # Get total size and duration
        from sqlalchemy import func
        result = db.query(
            func.sum(NerdcastEpisode.file_size_mb).label("total_size"),
            func.sum(NerdcastEpisode.duration_seconds).label("total_duration")
        ).first()
        
        total_size_mb = result.total_size or 0
        total_duration_seconds = result.total_duration or 0
        
        db.close()
        
        stats = {
            "total_episodes": total_episodes,
            "downloaded": downloaded,
            "transcribed": transcribed,
            "indexed": indexed,
            "total_size_mb": round(total_size_mb, 2),
            "total_duration_hours": round(total_duration_seconds / 3600, 2)
        }
        
        logger.info(f"✓ Total episodes: {total_episodes}")
        logger.info(f"  Downloaded: {downloaded}")
        logger.info(f"  Transcribed: {transcribed}")
        logger.info(f"  Indexed: {indexed}")
        logger.info(f"  Total size: {total_size_mb:.2f}MB")
        logger.info(f"  Total duration: {total_duration_seconds / 3600:.2f}h")
        logger.info("=" * 60)
        
        return stats
    
    except Exception as e:
        log.error(f"Failed to get episode stats: {e}")
        logger.error(f"Failed to get episode stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class FiltersResponse(BaseModel):
    """Available filters response model"""
    feeds: List[str]
    programs: List[str]


@router.get("/filters", response_model=FiltersResponse, tags=["filters"])
def get_filters():
    """
    Get available filters (feeds and programs)
    
    Returns:
        Available podcast sources (feeds) and program names for filtering
    """
    try:
        db = get_db_session()
        
        # Get distinct feeds (podcast_source)
        feeds = db.query(PodcastEpisode.podcast_source).distinct().all()
        feeds = sorted([f[0] for f in feeds if f[0] is not None])
        
        # Get distinct programs (program_name)
        programs = db.query(PodcastEpisode.program_name).distinct().all()
        programs = sorted([p[0] for p in programs if p[0] is not None])
        
        db.close()
        
        return {
            "feeds": feeds,
            "programs": programs
        }
    
    except Exception as e:
        logger.error(f"Failed to get filters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/last-updated", tags=["episodes"])
def get_last_updated():
    """Return the most recent episode updated_at as DD/MM/YYYY, or '—' if unavailable."""
    try:
        from sqlalchemy import func
        db = get_db_session()
        last = db.query(func.max(PodcastEpisode.updated_at)).scalar()
        db.close()
        if last:
            return {"date": last.strftime("%d/%m/%Y")}
        return {"date": "—"}
    except Exception as e:
        logger.error(f"Failed to get last updated: {e}")
        return {"date": "—"}
