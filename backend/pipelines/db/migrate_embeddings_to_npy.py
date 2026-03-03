"""
Migrate embeddings from SQLite DB to .npy files

Extracts the `embedding` column from `podcast_segments`, saves it as two .npy files:
  - embeddings_matrix.npy  shape (N, D) float32 - the raw vectors
  - embeddings_ids.npy     shape (N,)    int32  - parallel embedding_id per row

Then drops the `embedding` column from the DB, reducing its size from ~435 MB to ~150 MB.

Usage:
    python -m backend.pipelines.db.migrate_embeddings_to_npy
"""
import sys
import sqlite3
import numpy as np

from backend.app.core.config import settings
from backend.app.core.logger import logger


def migrate():
    faiss_dir = settings.get_faiss_dir()
    matrix_path = faiss_dir / "embeddings_matrix.npy"
    ids_path = faiss_dir / "embeddings_ids.npy"
    db_path = str(settings.get_database_path())

    logger.header("MIGRATE EMBEDDINGS -> NPY")

    conn = sqlite3.connect(db_path)
    try:
        # ------------------------------------------------------------------ #
        # Check if embedding column still exists
        # ------------------------------------------------------------------ #
        cursor = conn.execute("PRAGMA table_info(podcast_segments)")
        cols = [row[1] for row in cursor.fetchall()]
        if "embedding" not in cols:
            logger.info("Column `embedding` not present — checking if .npy files exist...")
            if matrix_path.exists() and ids_path.exists():
                logger.success("Migration already done. Nothing to do.")
            else:
                logger.error(
                    "Column `embedding` absent but .npy files are missing. "
                    "Cannot migrate. Restore DB from backup."
                )
                sys.exit(1)
            return

        # ------------------------------------------------------------------ #
        # 1. Read all (embedding_id, embedding blob) rows ordered by embedding_id
        # ------------------------------------------------------------------ #
        logger.section("1/3 - Reading embeddings from DB...")
        rows = conn.execute(
            "SELECT embedding_id, embedding FROM podcast_segments "
            "ORDER BY embedding_id"
        ).fetchall()
        logger.info(f"Total rows: {len(rows)}")

        # Determine target dimension (most common)
        dim_counts: dict = {}
        for embedding_id, blob in rows:
            if blob is None:
                continue
            arr = np.frombuffer(blob, dtype="float32")
            dim_counts[arr.shape[0]] = dim_counts.get(arr.shape[0], 0) + 1

        if not dim_counts:
            logger.error("No embeddings found in DB. Nothing to migrate.")
            sys.exit(1)

        target_dim = max(dim_counts, key=dim_counts.get)
        logger.info(f"Target dimension: {target_dim}  (distribution: {dim_counts})")

        # ------------------------------------------------------------------ #
        # 2. Extract and save as .npy
        # ------------------------------------------------------------------ #
        logger.section("2/3 - Saving embeddings to .npy files...")
        embeddings_list = []
        ids_list = []
        skipped = 0

        for embedding_id, blob in rows:
            if blob is None:
                skipped += 1
                continue
            arr = np.frombuffer(blob, dtype="float32")
            if arr.shape[0] != target_dim:
                skipped += 1
                continue
            embeddings_list.append(arr)
            ids_list.append(embedding_id)

        if skipped:
            logger.warning(f"Skipped {skipped} rows (null or wrong dimension)")

        matrix = np.array(embeddings_list, dtype="float32")
        ids_arr = np.array(ids_list, dtype="int32")

        faiss_dir.mkdir(parents=True, exist_ok=True)
        np.save(str(matrix_path), matrix)
        np.save(str(ids_path), ids_arr)

        logger.success(f"Saved embeddings_matrix.npy  shape={matrix.shape}")
        logger.success(f"Saved embeddings_ids.npy     shape={ids_arr.shape}")

        # ------------------------------------------------------------------ #
        # 3. Drop `embedding` column and vacuum
        # ------------------------------------------------------------------ #
        logger.section("3/3 - Dropping `embedding` column from podcast_segments...")
        conn.execute("ALTER TABLE podcast_segments DROP COLUMN embedding")
        conn.execute("VACUUM")
        conn.commit()
        logger.success("Column `embedding` dropped and DB vacuumed.")

    finally:
        conn.close()

    logger.header("MIGRATION COMPLETE")
    logger.info(f"embeddings_matrix.npy : {matrix_path}")
    logger.info(f"embeddings_ids.npy    : {ids_path}")


if __name__ == "__main__":
    migrate()
