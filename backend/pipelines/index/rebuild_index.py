"""
Rebuild FAISS index from embeddings_matrix.npy

This script rebuilds the FAISS search index from the pre-saved .npy embedding
files (generated during ingestion or by migrate_embeddings_to_npy.py).

Use this after:
- Changing FAISS index type (e.g., IndexFlatIP to IVF/HNSW)
- Corruption of the FAISS index file
- Adding new segments (ingestion already calls this automatically)

Usage:
    python -m backend.pipelines.index.rebuild_index
"""
import sys
import numpy as np
import faiss

from backend.app.core.config import settings
from backend.app.core.logger import logger, format_path


def rebuild_faiss_index():
    """
    Rebuild FAISS index from embeddings_matrix.npy and embeddings_ids.npy.

    Returns:
        Tuple of (index_path, total_vectors) or (None, 0) on error
    """
    logger.section("Rebuilding FAISS index from .npy embeddings")

    faiss_dir = settings.get_faiss_dir()
    index_path = settings.get_faiss_index_path()
    matrix_path = faiss_dir / "embeddings_matrix.npy"
    ids_path = faiss_dir / "embeddings_ids.npy"

    # Load embeddings from .npy files
    if not matrix_path.exists():
        logger.error(f"embeddings_matrix.npy not found at {format_path(matrix_path)}")
        logger.info("Run: python -m backend.pipelines.db.migrate_embeddings_to_npy")
        return None, 0

    if not ids_path.exists():
        logger.error(f"embeddings_ids.npy not found at {format_path(ids_path)}")
        logger.info("Run: python -m backend.pipelines.db.migrate_embeddings_to_npy")
        return None, 0

    logger.info(f"Loading {format_path(matrix_path)}")
    embeddings = np.load(str(matrix_path))
    embedding_ids = np.load(str(ids_path))

    if embeddings.ndim != 2 or len(embeddings) == 0:
        logger.error(f"embeddings_matrix.npy has unexpected shape: {embeddings.shape}")
        return None, 0

    if len(embeddings) != len(embedding_ids):
        logger.error(
            f"Shape mismatch: matrix has {len(embeddings)} rows "
            f"but ids has {len(embedding_ids)} entries"
        )
        return None, 0

    logger.success(f"Loaded {len(embeddings)} embeddings (dimension {embeddings.shape[1]})")

    # Build FAISS index
    logger.info("Building FAISS index...")
    embeddings = embeddings.astype("float32")
    dimension = embeddings.shape[1]

    # Normalize to unit length: IndexFlatIP on normalized vectors = cosine similarity
    faiss.normalize_L2(embeddings)
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    # Save index and mapping
    faiss_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Saving index to {format_path(index_path)}")
    faiss.write_index(index, str(index_path))

    mapping_path = faiss_dir / "embedding_id_mapping.npy"
    np.save(str(mapping_path), embedding_ids.astype("int32"))

    logger.success("FAISS index rebuilt successfully!")
    logger.info("  Index type : IndexFlatIP (cosine similarity)")
    logger.info(f"  Dimension  : {dimension}")
    logger.info(f"  Vectors    : {index.ntotal}")
    logger.info(f"  Mapping    : {mapping_path.name}")

    return index_path, index.ntotal


def main():
    """Main entry point for standalone execution"""
    logger.header("FAISS INDEX REBUILD")

    try:
        index_path, total = rebuild_faiss_index()

        if index_path:
            logger.header("REBUILD COMPLETE!")
            logger.info(f"Index saved  : {format_path(index_path)}")
            logger.info(f"Total vectors: {total}")
        else:
            logger.error("Rebuild failed")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Rebuild failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
