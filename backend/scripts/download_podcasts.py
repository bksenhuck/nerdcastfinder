"""
Download Nerdcast podcast episodes from RSS feed

This script:
1. Fetches the Nerdcast RSS feed
2. Downloads all episode audio files
3. Saves them to backend/data/podcasts/
4. Skips already downloaded files (idempotent)
5. Saves episode metadata (title, duration, date, size) to database

Usage:
    python -m scripts.download_podcasts
    
Options:
    --limit N : Download only the first N episodes
    --max-workers N : Number of concurrent downloads (default: 2)
"""
import sys
import re
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import feedparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config.settings import settings
from app.utils.logger import logger


def create_session() -> requests.Session:
    """
    Create a requests session with retry logic
    
    Returns:
        Configured requests Session
    """
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=settings.DOWNLOAD_MAX_RETRIES,
        backoff_factor=settings.DOWNLOAD_BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


def normalize_filename(title: str) -> str:
    """
    Normalize episode title to safe filename
    
    Args:
        title: Episode title
        
    Returns:
        Safe filename without extension
    """
    # Convert to lowercase
    filename = title.lower()
    
    # Replace spaces with underscores
    filename = filename.replace(" ", "_")
    
    # Remove invalid filesystem characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Remove special characters, keep only alphanumeric, underscore, hyphen
    filename = re.sub(r'[^\w\-]', '', filename)
    
    # Remove multiple underscores
    filename = re.sub(r'_+', '_', filename)
    
    # Trim underscores from start/end
    filename = filename.strip('_')
    
    # Limit length (Windows has 255 char path limit)
    max_length = 200
    if len(filename) > max_length:
        filename = filename[:max_length].rstrip('_')
    
    return filename


def fetch_feed(feed_url: str) -> Optional[feedparser.FeedParserDict]:
    """
    Fetch and parse RSS feed
    
    Args:
        feed_url: URL of the RSS feed
        
    Returns:
        Parsed feed or None if error
    """
    try:
        feed = feedparser.parse(feed_url)
        
        if feed.bozo:
            logger.warning("⚠️  Feed com problemas de parsing")
        
        if not feed.entries:
            logger.error("❌ Nenhum episódio encontrado no feed")
            return None
        
        logger.success(f"Found {len(feed.entries)} episodes in feed")
        return feed
        
    except Exception as e:
        logger.error(f"Failed to fetch feed: {e}")
        return None


def extract_episode_info(entry: feedparser.FeedParserDict) -> Optional[Dict]:
    """
    Extract episode information from feed entry
    
    Args:
        entry: Feed entry
        
    Returns:
        Dict with title, audio_url, duration, published_date, enclosure_length
    """
    try:
        title = entry.get('title', '').strip()
        if not title:
            return None
        
        # Get audio URL from enclosure
        enclosures = entry.get('enclosures', [])
        if not enclosures:
            return None
        
        # Find audio enclosure
        audio_url = None
        enclosure_length = None  # Size in bytes
        for enclosure in enclosures:
            if 'audio' in enclosure.get('type', ''):
                audio_url = enclosure.get('href', '')
                enclosure_length = enclosure.get('length', '')
                break
        
        if not audio_url:
            # Fallback: use first enclosure if no audio type found
            audio_url = enclosures[0].get('href', '')
            enclosure_length = enclosures[0].get('length', '')
        
        if not audio_url:
            return None
        
        # Extract duration (often in itunes:duration tag)
        duration_seconds = None
        if 'itunes_duration' in entry:
            duration_str = entry.get('itunes_duration', '')
            try:
                # Handle format: "HH:MM:SS" or just seconds
                if ':' in str(duration_str):
                    parts = str(duration_str).split(':')
                    duration_seconds = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                else:
                    duration_seconds = int(duration_str)
            except (ValueError, IndexError):
                pass
        
        # Extract published date
        published_date = None
        if 'published_parsed' in entry and entry['published_parsed']:
            try:
                published_date = datetime(*entry['published_parsed'][:6])
            except (TypeError, ValueError):
                pass
        
        return {
            'title': title,
            'audio_url': audio_url,
            'duration_seconds': duration_seconds,
            'published_date': published_date,
            'enclosure_length': int(enclosure_length) if enclosure_length else None
        }
        
    except Exception as e:
        logger.error(f"Error extracting episode info: {e}")
        return None


def save_episode_metadata(
    filename: str,
    title_original: str,
    audio_url: str,
    file_size_mb: float,
    duration_seconds: int = None,
    published_date = None
) -> Tuple[bool, str]:
    """
    Save or update episode metadata to database
    
    Args:
        filename: Normalized filename (unique key)
        title_original: Original title from RSS
        audio_url: URL of the audio file
        file_size_mb: Size of downloaded file in MB
        duration_seconds: Duration in seconds (optional)
        published_date: Publication date (optional)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        from app.db.session import get_db_session
        from app.db.models import NerdcastEpisode
        
        db = get_db_session()
        
        # Check if episode already exists
        existing = db.query(NerdcastEpisode).filter(
            NerdcastEpisode.filename == filename
        ).first()
        
        if existing:
            # Update ALL episode metadata
            existing.title_original = title_original
            existing.audio_url = audio_url
            existing.file_size_mb = file_size_mb
            existing.duration_seconds = duration_seconds
            existing.published_date = published_date
            existing.status = "downloaded"
            db.commit()
            db.close()
            return True, "atualizado"
        else:
            # Create new episode record
            episode = NerdcastEpisode(
                filename=filename,
                title_original=title_original,
                audio_url=audio_url,
                file_size_mb=file_size_mb,
                duration_seconds=duration_seconds,
                published_date=published_date,
                status="downloaded"
            )
            db.add(episode)
            db.commit()
            db.close()
            return True, "novo"
        
    except Exception as e:
        logger.warning(f"⚠️  Erro ao salvar metadados: {type(e).__name__}")
        return False, "erro"


def download_episode(
    episode: Dict,
    output_dir: Path,
    session: requests.Session
) -> Tuple[bool, str]:
    """
    Download a single episode and save metadata to database
    
    Args:
        episode: Dict with title, audio_url, duration_seconds, published_date, enclosure_length
        output_dir: Directory to save the file
        session: Requests session
        
    Returns:
        Tuple of (success, message)
    """
    title = episode['title']
    audio_url = episode['audio_url']
    
    # Normalize filename
    filename = normalize_filename(title)
    output_path = output_dir / f"{filename}.mp3"
    
    # Check if already exists
    if output_path.exists():
        return True, f"✓ Pulado (já existe): {title}"
    
    try:
        # Stream download
        response = session.get(
            audio_url,
            stream=True,
            timeout=settings.DOWNLOAD_TIMEOUT
        )
        response.raise_for_status()
        
        # Download file
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=settings.DOWNLOAD_CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
        
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        
        # Save metadata to database
        save_episode_metadata(
            filename=filename,
            title_original=title,
            audio_url=audio_url,
            file_size_mb=file_size_mb,
            duration_seconds=episode.get('duration_seconds'),
            published_date=episode.get('published_date')
        )
        
        return True, f"✓ Download: {title} ({file_size_mb:.1f}MB) → DB salvando metadados"
        
    except requests.exceptions.Timeout:
        return False, f"Timeout downloading: {title}"
    except requests.exceptions.RequestException as e:
        return False, f"Error downloading {title}: {e}"
    except IOError as e:
        return False, f"Error saving {title}: {e}"


def download_episodes_parallel(
    episodes: List[Dict[str, str]],
    output_dir: Path,
    max_workers: int = None
) -> Tuple[int, int]:
    """
    Download episodes in parallel
    
    Args:
        episodes: List of episode dicts
        output_dir: Output directory
        max_workers: Maximum concurrent downloads (default: from settings)
        
    Returns:
        Tuple of (success_count, failed_count)
    """
    if max_workers is None:
        max_workers = settings.DOWNLOAD_MAX_CONCURRENT
    success_count = 0
    failed_count = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create session for each worker
        session = create_session()
        
        # Submit all downloads
        future_to_episode = {
            executor.submit(download_episode, ep, output_dir, session): ep
            for ep in episodes
        }
        
        # Process completed downloads
        for future in as_completed(future_to_episode):
            episode = future_to_episode[future]
            try:
                success, message = future.result()
                if success:
                    logger.success(message)
                    success_count += 1
                else:
                    logger.error(message)
                    failed_count += 1
            except Exception as e:
                logger.error(f"Unexpected error for {episode['title']}: {e}")
                failed_count += 1
    
    return success_count, failed_count


def main(limit: Optional[int] = None, max_workers: Optional[int] = None):
    """
    Main entry point
    
    Args:
        limit: Limit number of episodes to download (None = all)
        max_workers: Number of concurrent downloads (None = from settings)
    """
    if max_workers is None:
        max_workers = settings.DOWNLOAD_MAX_CONCURRENT
    logger.header("📥 NERDCAST PODCAST DOWNLOADER")
    
    # Ensure output directory exists
    output_dir = settings.get_podcasts_dir()
    
    # Fetch RSS feed
    feed = fetch_feed(settings.RSS_FEED_URL)
    if not feed:
        logger.error("❌ Falha ao buscar feed")
        return 1
    
    # Extract episode information
    episodes = []
    for entry in feed.entries:
        episode_info = extract_episode_info(entry)
        if episode_info:
            episodes.append(episode_info)
    
    if not episodes:
        logger.error("❌ Nenhum episódio válido encontrado")
        return 1
    
    logger.success(f"✓ {len(episodes)} episódios encontrados")
    
    # Apply limit if specified
    if limit and limit > 0:
        episodes = episodes[:limit]
    
    # Download episodes
    logger.section(f"Baixando {len(episodes)} episódios (workers: {max_workers})...")
    
    start_time = time.time()
    success_count, failed_count = download_episodes_parallel(
        episodes,
        output_dir,
        max_workers=max_workers
    )
    elapsed_time = time.time() - start_time
    
    # Summary
    logger.section("📊 RESUMO")
    logger.success(f"✓ Baixados: {success_count}/{len(episodes)}")
    if failed_count > 0:
        logger.error(f"❌ Falhados: {failed_count}")
    logger.info(f"⏱️  Tempo: {elapsed_time:.1f}s")
    
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Download Nerdcast podcast episodes"
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of episodes to download'
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=None,
        help=f'Number of concurrent downloads (default: {settings.DOWNLOAD_MAX_CONCURRENT})'
    )
    
    args = parser.parse_args()
    
    exit_code = main(limit=args.limit, max_workers=args.max_workers)
    sys.exit(exit_code)
