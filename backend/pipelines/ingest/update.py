"""
Incremental update pipeline — download and index only what is missing from FAISS.

For each configured podcast this script:
1. Fetches the RSS feed
2. Compares feed episodes against what is already on disk and indexed in FAISS
3. Downloads any missing audio files
4. Transcribes + embeds episodes that are not yet in the FAISS index
5. Rebuilds the FAISS index once at the end (after all podcasts are processed)

Usage:
    python -m backend.pipelines.ingest.update
    python -m backend.pipelines.ingest.update --podcast nerdcast
    python -m backend.pipelines.ingest.update --dry-run
    python -m backend.pipelines.ingest.update --podcast nerdcast --dry-run
    python -m backend.pipelines.ingest.update --max-workers 4

Options:
    --podcast NAME   Process only the specified podcast (default: all)
    --dry-run        Show what would be done without making any changes
    --max-workers N  Parallel download workers (default: from settings)
"""
import sys
from typing import Dict, List, Optional, Set, Tuple

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.db.session import init_db
from backend.app.utils.faiss_utils import get_episodes_in_faiss, load_computed_embedding_ids
from backend.app.utils.rss_utils import extract_episode_info, fetch_feed, normalize_filename
from backend.pipelines.index.rebuild_index import rebuild_faiss_index


def get_podcast_status(podcast_id: str, podcast_config: dict) -> Dict:
    """
    Analyse the current state of a podcast against its RSS feed.

    Returns a dict with:
        podcast_id, podcast_name,
        total_in_feed      — number of episodes in the RSS
        on_disk            — number of audio files on disk
        indexed            — number of episodes fully in FAISS
        need_download      — list of episode dicts missing from disk
        need_index         — list of episode dicts on disk but not yet indexed
        error              — set if something went wrong (other keys may be absent)
    """
    podcast_dir = settings.get_podcasts_dir(podcast_id)

    # 1. Fetch RSS feed
    feed = fetch_feed(podcast_config["feed_url"])
    if not feed:
        return {"error": f"Could not fetch feed for {podcast_id}"}

    # 2. Parse all episodes and attach normalized filename
    feed_episodes: List[Dict] = []
    for entry in feed.entries:
        info = extract_episode_info(entry)
        if info:
            info["filename"] = normalize_filename(info["title"])
            feed_episodes.append(info)

    if not feed_episodes:
        return {"error": f"No valid episodes found in feed for {podcast_id}"}

    # 3. Files already on disk
    disk_files: Set[str] = (
        {f.stem for f in podcast_dir.glob("*.mp3")} if podcast_dir.exists() else set()
    )

    # 4. Episodes already indexed in FAISS
    indexed_ids = load_computed_embedding_ids()
    indexed_episodes = get_episodes_in_faiss(podcast_id, indexed_ids)

    # 5. Compute what needs work
    need_download = [ep for ep in feed_episodes if ep["filename"] not in disk_files]
    need_index = [
        ep
        for ep in feed_episodes
        if ep["filename"] in disk_files and ep["filename"] not in indexed_episodes
    ]

    return {
        "podcast_id": podcast_id,
        "podcast_name": podcast_config["name"],
        "total_in_feed": len(feed_episodes),
        "on_disk": len(disk_files),
        "indexed": len(indexed_episodes),
        "need_download": need_download,
        "need_index": need_index,
    }


# ---------------------------------------------------------------------------
# Update pipeline
# ---------------------------------------------------------------------------

class UpdatePipeline:
    """
    Incremental pipeline that brings the FAISS index up-to-date with the RSS feeds.

    Only processes episodes that are genuinely missing — download or indexing is
    skipped for episodes that are already present.
    """

    def __init__(
        self,
        podcast_name: Optional[str] = None,
        dry_run: bool = False,
        max_workers: Optional[int] = None,
    ):
        self.dry_run = dry_run
        self.max_workers = max_workers or settings.DOWNLOAD_MAX_CONCURRENT

        if podcast_name:
            if podcast_name not in settings.PODCASTS:
                raise ValueError(f"Podcast '{podcast_name}' not found in config")
            self.podcasts = {podcast_name: settings.PODCASTS[podcast_name]}
        else:
            self.podcasts = settings.PODCASTS

    def run(self) -> bool:
        mode = " [DRY RUN]" if self.dry_run else ""
        logger.header(f"UPDATE PIPELINE — Incremental RSS sync{mode}")

        init_db()

        all_ok = True
        total_downloaded = 0
        total_indexed = 0

        for podcast_id, podcast_config in self.podcasts.items():
            ok, n_dl, n_idx = self._process_podcast(podcast_id, podcast_config)
            all_ok = all_ok and ok
            total_downloaded += n_dl
            total_indexed += n_idx

        # Rebuild FAISS once after all podcasts (only if something new was indexed)
        if total_indexed > 0 and not self.dry_run:
            logger.section("Rebuilding FAISS index...")
            index_path, total_vectors = rebuild_faiss_index()
            if index_path:
                logger.success(f"FAISS index rebuilt: {total_vectors} vectors")
            else:
                logger.error("FAISS index rebuild failed")
                all_ok = False
        elif total_indexed == 0 and not self.dry_run:
            logger.info("Nothing new to index — FAISS is already up-to-date.")

        logger.header("UPDATE COMPLETE")
        if not self.dry_run:
            logger.success(f"New downloads : {total_downloaded}")
            logger.success(f"New indexed   : {total_indexed}")

        return all_ok

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _process_podcast(
        self, podcast_id: str, podcast_config: dict
    ) -> Tuple[bool, int, int]:
        """
        Check status, download missing audio, index un-indexed episodes.

        Returns (success, n_downloaded, n_indexed).
        """
        podcast_name = podcast_config["name"]
        logger.section(f"Podcast: {podcast_name}")

        status = get_podcast_status(podcast_id, podcast_config)

        if "error" in status:
            logger.error(status["error"])
            return False, 0, 0

        # Status report
        need_dl = len(status["need_download"])
        need_idx = len(status["need_index"])
        logger.info(f"  RSS feed  : {status['total_in_feed']} episodes")
        logger.info(f"  On disk   : {status['on_disk']}")
        logger.info(f"  Indexed   : {status['indexed']}")
        logger.info(f"  To download : {need_dl}")
        logger.info(f"  To index    : {need_idx + need_dl}")

        if self.dry_run:
            self._print_pending(status)
            return True, 0, 0

        if need_dl == 0 and need_idx == 0:
            logger.success("Already up-to-date.")
            return True, 0, 0

        n_downloaded = self._download_missing(podcast_id, status)
        n_indexed = self._index_missing(podcast_id, need_dl + need_idx)

        return True, n_downloaded, n_indexed

    def _print_pending(self, status: Dict) -> None:
        """Print a preview of what would be processed (dry-run mode)."""
        for label, key in [("To download", "need_download"), ("To index", "need_index")]:
            items = status[key]
            if not items:
                continue
            logger.info(f"\n  {label} ({len(items)}):")
            for ep in items[:10]:
                logger.info(f"    - {ep['title']}")
            if len(items) > 10:
                logger.info(f"    ... and {len(items) - 10} more")

    def _download_missing(self, podcast_id: str, status: Dict) -> int:
        """Download episodes listed in status['need_download']. Returns count downloaded."""
        episodes_to_download = status["need_download"]
        if not episodes_to_download:
            return 0

        logger.section(f"Downloading {len(episodes_to_download)} missing episodes...")
        output_dir = settings.get_podcasts_dir(podcast_id)

        from backend.pipelines.ingest.download import download_episodes_parallel

        success_count, failed_count = download_episodes_parallel(
            episodes_to_download,
            output_dir,
            podcast_name=podcast_id,
            max_workers=self.max_workers,
        )
        if failed_count:
            logger.warning(f"{failed_count} download(s) failed")
        return success_count

    def _index_missing(self, podcast_id: str, expected_count: int) -> int:
        """
        Transcribe and embed all episodes not yet in the FAISS index.

        Uses PodcastIngestionPipeline with pending_only=True so already-indexed
        episodes are skipped. skip_rebuild=True defers the FAISS rebuild to the
        caller (UpdatePipeline.run) so it happens only once for all podcasts.

        Returns the number of episodes that were expected to be indexed.
        """
        if expected_count == 0:
            return 0

        logger.section(f"Indexing {expected_count} episode(s) not yet in FAISS...")

        from backend.pipelines.ingest.ingest import PodcastIngestionPipeline

        try:
            pipeline = PodcastIngestionPipeline(
                podcast_name=podcast_id,
                pending_only=True,
                skip_rebuild=True,
            )
            pipeline.run()
        except Exception as e:
            logger.error(f"Indexing failed for {podcast_id}: {e}")
            return 0

        return expected_count


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(
    podcast_name: Optional[str] = None,
    dry_run: bool = False,
    max_workers: Optional[int] = None,
) -> int:
    try:
        pipeline = UpdatePipeline(
            podcast_name=podcast_name,
            dry_run=dry_run,
            max_workers=max_workers,
        )
        success = pipeline.run()
        return 0 if success else 1
    except ValueError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.error(f"Update failed: {e}")
        return 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Incremental update: download + index only episodes missing from FAISS"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--podcast",
        type=str,
        metavar="NAME",
        help="Process only the specified podcast (default: all configured podcasts)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making any changes",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help=f"Parallel download workers (default: {settings.DOWNLOAD_MAX_CONCURRENT})",
    )

    args = parser.parse_args()
    sys.exit(main(podcast_name=args.podcast, dry_run=args.dry_run, max_workers=args.max_workers))
