"""
FAISS index utilities — shared across ingest, update, and monitoring pipelines.

Provides:
  - load_indexed_embedding_ids()   what's actually searchable in the FAISS index
  - load_computed_embedding_ids()  what embeddings have been computed (pre-rebuild)
  - get_episodes_in_faiss()        which episodes are fully present in FAISS
  - append_embeddings_to_npy()     merge new embeddings into .npy files
"""
from typing import Dict, List, Set

import numpy as np

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.db.models import PodcastSegment
from backend.app.db.session import get_db_session


def load_indexed_embedding_ids() -> Set[int]:
    """
    Return the set of embedding IDs present in the FAISS index.

    Reads from embedding_id_mapping.npy — the mapping written by rebuild_index.
    Use this to check what is actually searchable right now.
    """
    mapping_path = settings.get_faiss_dir() / "embedding_id_mapping.npy"
    if not mapping_path.exists():
        return set()
    return set(np.load(str(mapping_path)).tolist())


def load_computed_embedding_ids() -> Set[int]:
    """
    Return the set of embedding IDs for which vectors have been computed.

    Reads from embeddings_ids.npy — the file maintained by append_embeddings_to_npy.
    Use this to check whether transcription + embedding has already been run
    (even if the FAISS index hasn't been rebuilt yet).
    """
    ids_path = settings.get_faiss_dir() / "embeddings_ids.npy"
    if not ids_path.exists():
        return set()
    return set(np.load(str(ids_path)).tolist())


def get_episodes_in_faiss(podcast_source: str, faiss_ids: Set[int]) -> Set[str]:
    """
    Return the set of episode filenames (stems) that are fully indexed in FAISS.

    An episode is considered indexed when ALL of its PodcastSegment rows have
    an embedding_id present in the provided faiss_ids set.

    Args:
        podcast_source: podcast key (e.g. "nerdcast")
        faiss_ids: set of embedding IDs to check against (from either load function)
    """
    db = get_db_session()
    try:
        rows = (
            db.query(PodcastSegment.episode, PodcastSegment.embedding_id)
            .filter(PodcastSegment.podcast_source == podcast_source)
            .all()
        )
    finally:
        db.close()

    if not rows:
        return set()

    episode_ids: Dict[str, List[int]] = {}
    for episode, emb_id in rows:
        episode_ids.setdefault(episode, []).append(emb_id)

    return {ep for ep, eids in episode_ids.items() if all(eid in faiss_ids for eid in eids)}


def append_embeddings_to_npy(new_ids: list, new_vecs: np.ndarray) -> None:
    """
    Merge new (embedding_id, vector) pairs into embeddings_matrix.npy /
    embeddings_ids.npy, then purge IDs no longer present in the DB.

    Called after each episode is transcribed and embedded, before the FAISS
    index is rebuilt.

    Args:
        new_ids: list of int embedding IDs
        new_vecs: float32 numpy array of shape (len(new_ids), embedding_dim)
    """
    faiss_dir = settings.get_faiss_dir()
    matrix_path = faiss_dir / "embeddings_matrix.npy"
    ids_path = faiss_dir / "embeddings_ids.npy"

    # Fetch all valid embedding_ids currently in the DB
    db = get_db_session()
    try:
        valid_ids: Set[int] = {
            row[0] for row in db.query(PodcastSegment.embedding_id).all()
        }
    finally:
        db.close()

    # Load existing matrix and keep only still-valid rows
    merged: Dict[int, np.ndarray] = {}
    if matrix_path.exists() and ids_path.exists():
        existing_ids = np.load(str(ids_path))
        existing_matrix = np.load(str(matrix_path))
        for i, eid in enumerate(existing_ids.tolist()):
            if eid in valid_ids:
                merged[eid] = existing_matrix[i]

    # Add new vectors (overwrite if re-ingesting same episode)
    for eid, vec in zip(new_ids, new_vecs):
        merged[eid] = vec.astype("float32")

    # Keep only valid IDs
    merged = {eid: vec for eid, vec in merged.items() if eid in valid_ids}

    if not merged:
        logger.warning("No embeddings to save to .npy")
        return

    ids_arr = np.array(list(merged.keys()), dtype="int32")
    matrix_arr = np.array(list(merged.values()), dtype="float32")

    faiss_dir.mkdir(parents=True, exist_ok=True)
    np.save(str(ids_path), ids_arr)
    np.save(str(matrix_path), matrix_arr)

    logger.success(f"Embeddings .npy updated: {len(ids_arr)} vectors saved")
