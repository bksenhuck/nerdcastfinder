"""
Download Nerdcast podcast episodes from RSS feed

This script:
1. Fetches the Nerdcast RSS feed
2. Downloads all episode audio files
3. Saves them to backend/data/podcasts/
4. Skips already downloaded files (idempotent)

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
    logger.info(f"Fetching RSS feed: {feed_url}")
    
    try:
        feed = feedparser.parse(feed_url)
        
        if feed.bozo:
            logger.warning("Feed has parsing issues, but continuing...")
        
        if not feed.entries:
            logger.error("No episodes found in feed")
            return None
        
        logger.success(f"Found {len(feed.entries)} episodes in feed")
        return feed
        
    except Exception as e:
        logger.error(f"Failed to fetch feed: {e}")
        return None


def extract_episode_info(entry: feedparser.FeedParserDict) -> Optional[Dict[str, str]]:
    """
    Extract episode information from feed entry
    
    Args:
        entry: Feed entry
        
    Returns:
        Dict with title and audio_url, or None if invalid
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
        for enclosure in enclosures:
            if 'audio' in enclosure.get('type', ''):
                audio_url = enclosure.get('href', '')
                break
        
        if not audio_url:
            # Fallback: use first enclosure if no audio type found
            audio_url = enclosures[0].get('href', '')
        
        if not audio_url:
            return None
        
        return {
            'title': title,
            'audio_url': audio_url
        }
        
    except Exception as e:
        logger.error(f"Error extracting episode info: {e}")
        return None


def download_episode(
    episode: Dict[str, str],
    output_dir: Path,
    session: requests.Session
) -> Tuple[bool, str]:
    """
    Download a single episode
    
    Args:
        episode: Dict with title and audio_url
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
        return True, f"Skipping (already exists): {title}"
    
    logger.info(f"Downloading: {title}")
    
    try:
        # Stream download
        response = session.get(
            audio_url,
            stream=True,
            timeout=settings.DOWNLOAD_TIMEOUT
        )
        response.raise_for_status()
        
        # Get file size if available
        total_size = int(response.headers.get('content-length', 0))
        
        # Download with progress
        downloaded = 0
        last_progress_shown = 0
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=settings.DOWNLOAD_CHUNK_SIZE):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Show progress every 10%
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        if progress - last_progress_shown >= 10:
                            logger.info(f"  Progress: {progress:.1f}%")
                            last_progress_shown = progress
        
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        return True, f"Downloaded: {title} ({file_size_mb:.1f} MB)"
        
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
    logger.header("NERDCAST PODCAST DOWNLOADER")
    
    # Ensure output directory exists
    output_dir = settings.get_podcasts_dir()
    logger.info(f"Output directory: {output_dir}")
    
    # Fetch RSS feed
    feed = fetch_feed(settings.RSS_FEED_URL)
    if not feed:
        logger.error("Failed to fetch feed. Exiting.")
        return 1
    
    # Extract episode information
    logger.section("Extracting episode information...")
    episodes = []
    for entry in feed.entries:
        episode_info = extract_episode_info(entry)
        if episode_info:
            episodes.append(episode_info)
    
    if not episodes:
        logger.error("No valid episodes found")
        return 1
    
    logger.success(f"Found {len(episodes)} valid episodes")
    
    # Apply limit if specified
    if limit and limit > 0:
        episodes = episodes[:limit]
        logger.info(f"Limiting to first {limit} episodes")
    
    # Download episodes
    logger.section(f"Downloading {len(episodes)} episodes...")
    logger.info(f"Using {max_workers} concurrent downloads")
    
    start_time = time.time()
    success_count, failed_count = download_episodes_parallel(
        episodes,
        output_dir,
        max_workers=max_workers
    )
    elapsed_time = time.time() - start_time
    
    # Summary
    logger.header("DOWNLOAD SUMMARY")
    logger.info(f"Total episodes: {len(episodes)}")
    logger.success(f"Successfully downloaded: {success_count}")
    if failed_count > 0:
        logger.error(f"Failed: {failed_count}")
    logger.info(f"Time elapsed: {elapsed_time:.1f} seconds")
    
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
