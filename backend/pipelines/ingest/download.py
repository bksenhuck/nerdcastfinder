"""
Download podcast episodes from RSS feeds

This script:
1. Fetches podcast RSS feeds
2. Downloads all episode audio files
3. Saves them to backend/data/podcasts/<podcast_name>/
4. Skips already downloaded files (idempotent)
5. Saves episode metadata (title, duration, date, size) to database

Usage:
    python -m backend.pipelines.ingest.download --list
    python -m backend.pipelines.ingest.download --podcast nerdcast
    python -m backend.pipelines.ingest.download --podcast nerdcast --limit 10
    python -m backend.pipelines.ingest.download --all
    
Options:
    --list : Show available podcasts
    --podcast NAME : Download specific podcast by name
    --all : Download all configured podcasts
    --limit N : Download only the first N episodes per podcast
    --max-workers N : Number of concurrent downloads (default: 2)
"""
import sys
import re
import time
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import feedparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.utils.program_utils import extract_program_from_title, normalize_program_name

# Thread lock for database writes (SQLite doesn't like concurrent writes)
_db_lock = threading.Lock()


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
        
        # Extract summary/description
        summary = entry.get('summary', '').strip()
        
        # Extract image URL
        image_url = None
        if 'image' in entry and isinstance(entry['image'], dict):
            image_url = entry['image'].get('href', '')
        
        # Extract program name from title
        program_name = extract_program_from_title(title)
        
        return {
            'title': title,
            'audio_url': audio_url,
            'duration_seconds': duration_seconds,
            'published_date': published_date,
            'enclosure_length': int(enclosure_length) if enclosure_length else None,
            'summary': summary,
            'image_url': image_url,
            'program_name': program_name
        }
        
    except Exception as e:
        logger.error(f"Error extracting episode info: {e}")
        return None


def save_episode_metadata(
    podcast_name: str,
    filename: str,
    title_original: str,
    audio_url: str,
    file_size_mb: float,
    duration_seconds: int = None,
    published_date = None,
    program_name: str = None,
    max_retries: int = 5
) -> Tuple[bool, str]:
    """
    Save or update episode metadata to database with retry logic for SQLite locks
    
    Args:
        podcast_name: Podcast/feed source name
        filename: Normalized filename (unique key)
        title_original: Original title from RSS
        audio_url: URL of the audio file
        file_size_mb: Size of downloaded file in MB
        duration_seconds: Duration in seconds (optional)
        published_date: Publication date (optional)
        program_name: Program name within feed (optional)
        max_retries: Max retry attempts (default: 5)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    for attempt in range(max_retries):
        try:
            # Use lock to serialize database writes
            with _db_lock:
                from backend.app.db.session import get_db_session
                from backend.app.db.models import PodcastEpisode
                
                db = get_db_session()
                
                # Check if episode already exists
                existing = db.query(PodcastEpisode).filter(
                    PodcastEpisode.filename == filename
                ).first()
                
                if existing:
                    # Update ALLepisode metadata
                    existing.podcast_source = podcast_name
                    existing.program_name = normalize_program_name(program_name, podcast_name)
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
                    episode = PodcastEpisode(
                        podcast_source=podcast_name,
                        program_name=normalize_program_name(program_name, podcast_name),
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
            if 'db' in locals():
                db.close()
            
            # Retry on operational errors (database locks)
            if attempt < max_retries - 1:
                wait_time = 0.2 * (2 ** attempt)  # Exponential backoff: 0.2s, 0.4s, 0.8s, 1.6s, 3.2s
                time.sleep(wait_time)
                continue
            else:
                logger.warning(f"⚠️  DB fail ({attempt+1} tries): {type(e).__name__}")
                return False, "erro"
    
    return False, "erro"


def download_episode(
    episode: Dict,
    output_dir: Path,
    session: requests.Session
) -> Tuple[bool, str, Dict]:
    """
    Download a single episode (don't save metadata yet - avoid DB locks)
    
    Args:
        episode: Dict with title, audio_url, duration_seconds, published_date
        output_dir: Directory to save the file
        session: Requests session
        
    Returns:
        Tuple of (success: bool, message: str, metadata: dict or None)
    """
    title = episode['title']
    audio_url = episode['audio_url']
    
    # Normalize filename
    filename = normalize_filename(title)
    output_path = output_dir / f"{filename}.mp3"
    
    # Prepare metadata (always return it, even if file exists)
    metadata_base = {
        'filename': filename,
        'title_original': title,
        'audio_url': audio_url,
        'duration_seconds': episode.get('duration_seconds'),
        'published_date': episode.get('published_date'),
        'summary': episode.get('summary'),
        'image_url': episode.get('image_url'),
        'program_name': episode.get('program_name')
    }

    # Check if already exists
    if output_path.exists():
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        metadata_base['file_size_mb'] = file_size_mb
        return True, f"✓ Pulado (já existe): {title}", metadata_base
    
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
        
        # Collect metadata for later batch insert
        metadata = {
            'filename': filename,
            'title_original': title,
            'audio_url': audio_url,
            'file_size_mb': file_size_mb,
            'duration_seconds': episode.get('duration_seconds'),
            'published_date': episode.get('published_date'),
            'summary': episode.get('summary'),
            'image_url': episode.get('image_url'),
            'program_name': episode.get('program_name')
        }

        return True, f"✓ Download: {title} ({file_size_mb:.1f}MB)", metadata
        
    except requests.exceptions.Timeout:
        return False, f"❌ Timeout: {title}", None
    except requests.exceptions.RequestException as e:
        return False, f"❌ Erro: {title}", None
    except IOError as e:
        return False, f"❌ Erro file: {title}", None


def download_episodes_parallel(
    episodes: List[Dict[str, str]],
    output_dir: Path,
    podcast_name: str,
    max_workers: int = None
) -> Tuple[int, int]:
    """
    Download episodes in parallel, collect metadata, then save to DB sequentially

    Args:
        episodes: List of episode dicts
        output_dir: Output directory
        podcast_name: Podcast source name (used when saving to DB)
        max_workers: Maximum concurrent downloads (default: from settings)

    Returns:
        Tuple of (success_count, failed_count)
    """
    if max_workers is None:
        max_workers = settings.DOWNLOAD_MAX_CONCURRENT
    success_count = 0
    failed_count = 0
    all_metadata = []
    
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
                success, message, metadata = future.result()
                if success:
                    logger.success(message)
                    success_count += 1
                    if metadata:  # Collect metadata for batch insert
                        all_metadata.append(metadata)
                else:
                    logger.error(message)
                    failed_count += 1
            except Exception as e:
                logger.error(f"Unexpected error for {episode['title']}: {e}")
                failed_count += 1
    
    # Save all metadata to database sequentially (avoid concurrent DB writes)
    if all_metadata:
        logger.section(f"Salvando {len(all_metadata)} metadados no DB...")
        db_success, db_error = save_all_episode_metadata(all_metadata, podcast_name)
        logger.success(f"✓ {db_success} salvos | ⚠️  {db_error} erros")
    
    return success_count, failed_count


def save_all_episode_metadata(metadata_list: List[Dict], podcast_name: str) -> Tuple[int, int]:
    """
    Save all episode metadata to database in batches with progress feedback

    Args:
        metadata_list: List of metadata dicts from downloads
        podcast_name: Podcast source name to store in DB

    Returns:
        Tuple of (success_count, error_count)
    """
    BATCH_SIZE = 100  # Commit a cada 100 episódios
    success_count = 0
    error_count = 0
    total = len(metadata_list)
    
    try:
        from backend.app.db.session import get_db_session, init_db
        from backend.app.db.models import PodcastEpisode
        
        # Ensure database and tables exist
        init_db()
        
        db = get_db_session()
        
        # Process in batches
        for batch_start in range(0, total, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, total)
            batch = metadata_list[batch_start:batch_end]
            batch_success = 0
            batch_errors = 0
            
            try:
                for metadata in batch:
                    try:
                        existing = db.query(PodcastEpisode).filter(
                            PodcastEpisode.filename == metadata['filename']
                        ).first()
                        
                        # Get or extract program name
                        program_name = metadata.get('program_name')
                        normalized_program = normalize_program_name(program_name, podcast_name)
                        
                        if existing:
                            existing.podcast_source = podcast_name
                            existing.program_name = normalized_program
                            existing.title_original = metadata['title_original']
                            existing.summary = metadata.get('summary')
                            existing.image_url = metadata.get('image_url')
                            existing.audio_url = metadata['audio_url']
                            existing.file_size_mb = metadata['file_size_mb']
                            existing.duration_seconds = metadata['duration_seconds']
                            existing.published_date = metadata['published_date']
                            existing.status = "downloaded"
                            existing.downloaded_at = datetime.utcnow()  # Atualiza timestamp do download
                        else:
                            episode = PodcastEpisode(
                                podcast_source=podcast_name,
                                program_name=normalized_program,
                                filename=metadata['filename'],
                                title_original=metadata['title_original'],
                                summary=metadata.get('summary'),
                                image_url=metadata.get('image_url'),
                                audio_url=metadata['audio_url'],
                                file_size_mb=metadata['file_size_mb'],
                                duration_seconds=metadata['duration_seconds'],
                                published_date=metadata['published_date'],
                                status="downloaded",
                                downloaded_at=datetime.utcnow()  # Timestamp do download
                            )
                            db.add(episode)
                        
                        batch_success += 1
                    except Exception as e:
                        logger.warning(f"⚠️  {metadata['filename']}: {type(e).__name__}: {str(e)}")
                        batch_errors += 1
                
                # Commit this batch
                db.commit()
                success_count += batch_success
                error_count += batch_errors
                
                # Show progress
                logger.info(f"  ✓ {batch_end}/{total} processados ({batch_success} salvos, {batch_errors} erros)")
                
            except Exception as e:
                logger.error(f"❌ Erro no batch {batch_start}-{batch_end}: {type(e).__name__}: {str(e)}")
                db.rollback()
                error_count += len(batch) - batch_success
        
        db.close()
    
    except Exception as e:
        logger.error(f"❌ Erro geral DB: {type(e).__name__}: {str(e)}")
        if 'db' in locals():
            db.rollback()
            db.close()
    
    return success_count, error_count


def main(limit: Optional[int] = None, max_workers: Optional[int] = None, podcast_name: Optional[str] = None):
    """
    Main entry point for downloading a specific podcast
    
    Args:
        limit: Limit number of episodes to download (None = all)
        max_workers: Number of concurrent downloads (None = from settings)
        podcast_name: Name of the podcast to download (must exist in settings.PODCASTS)
    """
    if max_workers is None:
        max_workers = settings.DOWNLOAD_MAX_CONCURRENT
    
    # Get podcast configuration
    if podcast_name not in settings.PODCASTS:
        logger.error(f"❌ Podcast '{podcast_name}' não encontrado")
        logger.info("Use --list para ver podcasts disponíveis")
        return 1
    
    podcast_config = settings.PODCASTS[podcast_name]
    podcast_display_name = podcast_config["name"]
    feed_url = podcast_config["feed_url"]
    
    logger.header(f"📥 DOWNLOAD: {podcast_display_name}")
    
    # Ensure output directory exists for this specific podcast
    output_dir = settings.get_podcasts_dir(podcast_name)
    
    # Fetch RSS feed
    feed = fetch_feed(feed_url)
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
        podcast_name=podcast_name,
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


def download_all_podcasts(limit: Optional[int] = None, max_workers: Optional[int] = None):
    """
    Download all configured podcasts
    
    Args:
        limit: Limit number of episodes per podcast (None = all)
        max_workers: Number of concurrent downloads (None = from settings)
        
    Returns:
        0 if all succeeded, 1 if any failed
    """
    logger.header("📥 DOWNLOAD ALL PODCASTS")
    
    podcasts = settings.PODCASTS
    total_podcasts = len(podcasts)
    failed_podcasts = []
    
    for idx, (podcast_id, podcast_config) in enumerate(podcasts.items(), 1):
        podcast_name = podcast_config["name"]
        logger.section(f"[{idx}/{total_podcasts}] {podcast_name}")
        
        exit_code = main(limit=limit, max_workers=max_workers, podcast_name=podcast_id)
        
        if exit_code != 0:
            failed_podcasts.append(podcast_name)
        
        # Pequena pausa entre podcasts
        if idx < total_podcasts:
            import time
            time.sleep(2)
    
    # Summary
    logger.header("📊 RESUMO GERAL")
    logger.success(f"✓ Processados: {total_podcasts} podcasts")
    
    if failed_podcasts:
        logger.error(f"❌ Falharam: {len(failed_podcasts)}")
        for name in failed_podcasts:
            logger.error(f"  - {name}")
        return 1
    else:
        logger.success("✓ Todos os podcasts baixados com sucesso!")
        return 0


def list_podcasts():
    """List all available podcasts"""
    logger.header("📻 PODCASTS DISPONÍVEIS")
    
    podcasts = settings.PODCASTS
    
    if not podcasts:
        logger.warning("Nenhum podcast configurado")
        return
    
    logger.info(f"Total: {len(podcasts)} podcast(s) configurado(s)\n")
    
    for podcast_id, config in podcasts.items():
        logger.info(f"🎙️  {config['name']}")
        logger.info(f"   ID: {podcast_id}")
        logger.info(f"   Feed: {config['feed_url']}")
        if 'description' in config:
            logger.info(f"   Descrição: {config['description']}")
        logger.info("")  # Blank line
    
    logger.info("Uso:")
    logger.info("  python -m backend.pipelines.download --podcast <ID>")
    logger.info("  python -m backend.pipelines.download --all")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Download podcast episodes from RSS feeds"
    )
    
    # Mutually exclusive group for podcast selection
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--list',
        action='store_true',
        help='List all available podcasts'
    )
    group.add_argument(
        '--podcast',
        type=str,
        metavar='NAME',
        help='Download specific podcast by name'
    )
    group.add_argument(
        '--all',
        action='store_true',
        help='Download all configured podcasts'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of episodes to download per podcast'
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=None,
        help=f'Number of concurrent downloads (default: {settings.DOWNLOAD_MAX_CONCURRENT})'
    )
    
    args = parser.parse_args()
    
    # Handle --list
    if args.list:
        list_podcasts()
        sys.exit(0)
    
    # Handle --all
    if args.all:
        exit_code = download_all_podcasts(limit=args.limit, max_workers=args.max_workers)
        sys.exit(exit_code)
    
    # Handle --podcast
    if args.podcast:
        exit_code = main(limit=args.limit, max_workers=args.max_workers, podcast_name=args.podcast)
        sys.exit(exit_code)
    
    # No arguments provided - show help
    parser.print_help()
    logger.info("\nDica: Use --list para ver podcasts disponíveis")
    sys.exit(1)
