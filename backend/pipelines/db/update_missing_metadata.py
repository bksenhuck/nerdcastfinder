"""
Backfill missing image_url and summary for all configured podcasts.

Fetches the RSS feed for each podcast and updates episodes in the DB that
have NULL image_url or summary. Checks both `image` and `itunes_image` feed
fields so podcasts like Nerdcast (which use itunes:image) are covered.

Usage:
    python -m backend.pipelines.db.update_missing_metadata
    python -m backend.pipelines.db.update_missing_metadata --podcast nerdcast
"""
import argparse
import sys

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.db.session import get_db_session
from backend.app.db.models import PodcastEpisode
from backend.app.utils.rss_utils import fetch_feed


def _extract_image(entry) -> str | None:
    """Return image URL from a feedparser entry (checks image + itunes_image)."""
    if "image" in entry and isinstance(entry["image"], dict):
        url = entry["image"].get("href") or None
        if url:
            return url
    if "itunes_image" in entry and isinstance(entry["itunes_image"], dict):
        url = entry["itunes_image"].get("href") or None
        if url:
            return url
    return None


def backfill_podcast(podcast_id: str, podcast_config: dict) -> None:
    podcast_name = podcast_config["name"]
    feed_url = podcast_config["feed_url"]

    logger.section(f"Podcast: {podcast_name}")
    feed = fetch_feed(feed_url)
    if not feed:
        logger.error(f"Could not fetch feed for {podcast_id}")
        return

    # Build lookup by title
    feed_data: dict[str, dict] = {}
    for entry in feed.entries:
        title = entry.get("title", "").strip()
        if title:
            feed_data[title] = {
                "summary": entry.get("summary", "").strip() or None,
                "image_url": _extract_image(entry),
            }

    logger.info(f"Feed has {len(feed_data)} episodes")

    db = get_db_session()
    try:
        episodes = (
            db.query(PodcastEpisode)
            .filter(
                PodcastEpisode.podcast_source == podcast_id,
                (PodcastEpisode.image_url == None) | (PodcastEpisode.summary == None),  # noqa: E711
            )
            .all()
        )
        logger.info(f"{len(episodes)} episodes need backfill")

        updated = 0
        not_found = 0
        for ep in episodes:
            data = feed_data.get(ep.title_original)
            if not data:
                not_found += 1
                continue
            if ep.image_url is None and data["image_url"]:
                ep.image_url = data["image_url"]
            if ep.summary is None and data["summary"]:
                ep.summary = data["summary"]
            updated += 1

        db.commit()
        logger.success(f"Updated {updated} episodes")
        if not_found:
            logger.warning(f"{not_found} episodes not found in feed (may be too old)")
    finally:
        db.close()


def main(podcast_name: str | None = None) -> None:
    logger.header("BACKFILL MISSING METADATA")

    podcasts = settings.PODCASTS
    if podcast_name:
        if podcast_name not in podcasts:
            logger.error(f"Podcast '{podcast_name}' not found in config")
            sys.exit(1)
        podcasts = {podcast_name: podcasts[podcast_name]}

    for podcast_id, podcast_config in podcasts.items():
        backfill_podcast(podcast_id, podcast_config)

    logger.success("Done")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill missing image_url/summary from RSS")
    parser.add_argument("--podcast", type=str, default=None, help="Process only this podcast")
    args = parser.parse_args()
    main(podcast_name=args.podcast)
