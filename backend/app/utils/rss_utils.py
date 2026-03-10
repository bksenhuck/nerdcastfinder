"""
RSS feed utilities — shared between download and update pipelines.

Provides: create_session, normalize_filename, fetch_feed, extract_episode_info
"""
import re
from datetime import datetime
from typing import Dict, Optional

import feedparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.utils.program_utils import extract_program_from_title


def create_session() -> requests.Session:
    """Create a requests session with retry logic."""
    session = requests.Session()
    retry_strategy = Retry(
        total=settings.DOWNLOAD_MAX_RETRIES,
        backoff_factor=settings.DOWNLOAD_BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def normalize_filename(title: str) -> str:
    """Normalize episode title to a safe filesystem filename (no extension)."""
    filename = title.lower().replace(" ", "_")
    filename = re.sub(r'[<>:"/\\|?*]', "", filename)
    filename = re.sub(r"[^\w\-]", "", filename)
    filename = re.sub(r"_+", "_", filename).strip("_")
    if len(filename) > 200:
        filename = filename[:200].rstrip("_")
    return filename


def fetch_feed(feed_url: str) -> Optional[feedparser.FeedParserDict]:
    """Fetch and parse an RSS feed. Returns None on error."""
    try:
        feed = feedparser.parse(feed_url)
        if feed.bozo:
            logger.warning("Feed with parsing issues")
        if not feed.entries:
            logger.error("No episodes found in feed")
            return None
        logger.success(f"Found {len(feed.entries)} episodes in feed")
        return feed
    except Exception as e:
        logger.error(f"Failed to fetch feed: {e}")
        return None


def extract_episode_info(entry: feedparser.FeedParserDict) -> Optional[Dict]:
    """
    Extract episode metadata from a feedparser entry.

    Returns a dict with keys:
        title, audio_url, duration_seconds, published_date,
        enclosure_length, summary, image_url, program_name
    Returns None if the entry is invalid or has no audio URL.
    """
    try:
        title = entry.get("title", "").strip()
        if not title:
            return None

        enclosures = entry.get("enclosures", [])
        if not enclosures:
            return None

        audio_url = None
        enclosure_length = None
        for enclosure in enclosures:
            if "audio" in enclosure.get("type", ""):
                audio_url = enclosure.get("href", "")
                enclosure_length = enclosure.get("length", "")
                break

        if not audio_url:
            audio_url = enclosures[0].get("href", "")
            enclosure_length = enclosures[0].get("length", "")

        if not audio_url:
            return None

        duration_seconds = None
        if "itunes_duration" in entry:
            duration_str = entry.get("itunes_duration", "")
            try:
                if ":" in str(duration_str):
                    parts = str(duration_str).split(":")
                    duration_seconds = (
                        int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    )
                else:
                    duration_seconds = int(duration_str)
            except (ValueError, IndexError):
                pass

        published_date = None
        if "published_parsed" in entry and entry["published_parsed"]:
            try:
                published_date = datetime(*entry["published_parsed"][:6])
            except (TypeError, ValueError):
                pass

        image_url = None
        if "image" in entry and isinstance(entry["image"], dict):
            image_url = entry["image"].get("href") or None
        if not image_url and "itunes_image" in entry and isinstance(entry["itunes_image"], dict):
            image_url = entry["itunes_image"].get("href") or None

        return {
            "title": title,
            "audio_url": audio_url,
            "duration_seconds": duration_seconds,
            "published_date": published_date,
            "enclosure_length": int(enclosure_length) if enclosure_length else None,
            "summary": entry.get("summary", "").strip(),
            "image_url": image_url,
            "program_name": extract_program_from_title(title),
        }

    except Exception as e:
        logger.error(f"Error extracting episode info: {e}")
        return None
