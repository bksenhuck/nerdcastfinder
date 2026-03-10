"""
Re-embed all segments in the database using the current embedding model.

Use this after changing the EMBEDDING_MODEL in config.py to regenerate
all embeddings without re-running the full ingestion pipeline (no Whisper needed).

Usage:
    python -m backend.pipelines.embed.reembed_segments
    python -m backend.pipelines.embed.reembed_segments --podcast pelada_na_net
    python -m backend.pipelines.embed.reembed_segments --dry-run
"""
import sys
import argparse
import numpy as np

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.db.session import get_db_session
from backend.app.db.models import PodcastSegment
from backend.app.services.embedding_service import EmbeddingService
from backend.pipelines.index.rebuild_index import rebuild_faiss_index


def reembed_segments(podcast_name: str = None, dry_run: bool = False) -> bool:
    """
    Re-generate embeddings for all segments using the current model.

    Args:
        podcast_name: If set, only re-embed segments from this podcast source.
        dry_run: If True, only count and report — do not modify the DB.

    Returns:
        True on success, False on error.
    """
    logger.header("RE-EMBED SEGMENTS")
    logger.info(f"Model: {settings.EMBEDDING_MODEL}")

    if podcast_name:
        logger.info(f"Filter: podcast_source = '{podcast_name}'")
    else:
        logger.info("Filter: all podcasts")

    if dry_run:
        logger.info("Mode: DRY RUN (no changes will be made)")

    db = get_db_session()

    try:
        # Load segments
        logger.section("[1/3] Loading segments from database...")
        query = db.query(PodcastSegment)
        if podcast_name:
            query = query.filter(PodcastSegment.podcast_source == podcast_name)

        segments = query.order_by(PodcastSegment.id).all()

        if not segments:
            logger.warning("No segments found matching the criteria.")
            return False

        logger.success(f"Found {len(segments)} segments to re-embed")

        if dry_run:
            logger.info("Dry run complete — no changes made.")
            return True

        # Load embedding model
        logger.section("[2/3] Generating new embeddings...")
        embedding_service = EmbeddingService()
        embedding_service.load_model()

        batch_size = settings.EMBEDDING_BATCH_SIZE
        total = len(segments)
        errors = 0

        # Load existing .npy as base so we preserve embeddings from other podcasts
        # when running a partial reembed (--podcast filter).
        faiss_dir = settings.get_faiss_dir()
        matrix_path = faiss_dir / "embeddings_matrix.npy"
        ids_path = faiss_dir / "embeddings_ids.npy"

        merged: dict = {}  # embedding_id -> vector
        if matrix_path.exists() and ids_path.exists():
            existing_ids = np.load(str(ids_path))
            existing_matrix = np.load(str(matrix_path))
            for i, eid in enumerate(existing_ids.tolist()):
                merged[eid] = existing_matrix[i]
            logger.info(f"  Loaded {len(merged)} existing vectors from .npy")

        for batch_start in range(0, total, batch_size):
            batch = segments[batch_start: batch_start + batch_size]
            texts = [seg.content for seg in batch]

            try:
                embeddings = embedding_service.generate_embeddings(
                    texts,
                    batch_size=batch_size,
                    show_progress=False,
                    is_query=False,
                )

                for seg, emb in zip(batch, embeddings):
                    merged[seg.embedding_id] = emb.astype("float32")

                progress = min(batch_start + batch_size, total)
                logger.info(f"  Progress: {progress}/{total} segments")

            except Exception as e:
                errors += 1
                logger.error(f"  Batch error at {batch_start}: {e}")
                logger.warning("  Skipping batch and continuing...")
                continue

        updated = total - (errors * batch_size)

        # Write merged vectors to .npy
        if not merged:
            logger.error("No embeddings to save")
            return False

        ids_arr = np.array(list(merged.keys()), dtype="int32")
        matrix_arr = np.array(list(merged.values()), dtype="float32")
        faiss_dir.mkdir(parents=True, exist_ok=True)
        np.save(str(ids_path), ids_arr)
        np.save(str(matrix_path), matrix_arr)
        logger.success(f"Saved {len(ids_arr)} vectors to .npy")

        logger.success(f"Re-embedded ~{updated}/{total} segments ({errors} batch errors)")

        # Rebuild FAISS index
        logger.section("[3/3] Rebuilding FAISS index...")
        index_path, total_vectors = rebuild_faiss_index()

        if index_path:
            logger.success(f"FAISS index rebuilt: {total_vectors} vectors")
        else:
            logger.error("FAISS index rebuild failed")
            return False

        logger.header("RE-EMBED COMPLETE!")
        logger.info(f"Segments updated: {updated}")
        logger.info(f"Vectors in index: {total_vectors}")
        logger.info(f"Model used: {settings.EMBEDDING_MODEL}")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Re-embed failed: {e}")
        return False
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Re-embed podcast segments using the current embedding model"
    )
    parser.add_argument(
        "--podcast",
        type=str,
        metavar="NAME",
        help="Re-embed only segments from this podcast source (e.g. pelada_na_net)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count segments without making any changes"
    )
    args = parser.parse_args()

    success = reembed_segments(
        podcast_name=args.podcast,
        dry_run=args.dry_run
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
