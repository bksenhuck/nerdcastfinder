"""
Rebuild FAISS index from database embeddings

This script rebuilds the FAISS search index from all segment embeddings
stored in the SQLite database. Use this after:
- Changing embedding models
- Database corruption
- Adding new segments without rebuilding index

Usage:
    python -m backend.pipelines.rebuild_index
"""
import sys
import numpy as np
import faiss
from pathlib import Path

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.db.session import get_db_session
from backend.app.db.models import PodcastSegment


def rebuild_faiss_index():
    """
    Rebuild FAISS index from all embeddings stored in database
    
    Returns:
        Tuple of (index_path, total_vectors) or (None, 0) on error
    """
    logger.section("🔨 Rebuilding FAISS index from database")
    
    db = get_db_session()
    faiss_dir = settings.get_faiss_dir()
    index_path = settings.get_faiss_index_path()
    
    try:
        # Load all segments ordered by embedding_id
        logger.info("📊 Loading segments from database...")
        segments = db.query(PodcastSegment).order_by(PodcastSegment.embedding_id).all()
        
        if not segments:
            logger.warning("⚠️  No segments found in database!")
            return None, 0
        
        logger.success(f"✓ Found {len(segments)} segments")
        
        # Extract embeddings and embedding_ids
        logger.info("🔄 Extracting embeddings...")
        embeddings_list = []
        embedding_ids = []
        skipped_no_emb = 0
        skipped_wrong_dim = 0
        dimension_target = None
        
        # First pass: determine target dimension (most common)
        dim_counts = {}
        for segment in segments:
            emb = segment.get_embedding()
            if emb is not None:
                dim = emb.shape[0]
                dim_counts[dim] = dim_counts.get(dim, 0) + 1
        
        if dim_counts:
            dimension_target = max(dim_counts, key=dim_counts.get)
            logger.info(f"🎯 Target dimension: {dimension_target} ({dim_counts[dimension_target]} segments)")
            if len(dim_counts) > 1:
                logger.warning(f"⚠️  Mixed dimensions detected: {dim_counts}")
                logger.warning(f"⚠️  Will only use {dimension_target}-dim embeddings")
        
        # Second pass: collect embeddings with target dimension
        for segment in segments:
            emb = segment.get_embedding()
            if emb is None:
                skipped_no_emb += 1
                continue
            
            if emb.shape[0] != dimension_target:
                skipped_wrong_dim += 1
                continue
                
            embeddings_list.append(emb)
            embedding_ids.append(segment.embedding_id)
        
        if skipped_no_emb > 0:
            logger.warning(f"⚠️  Skipped {skipped_no_emb} segments without embeddings")
        if skipped_wrong_dim > 0:
            logger.warning(f"⚠️  Skipped {skipped_wrong_dim} segments with wrong dimension (old model)")
        
        if not embeddings_list:
            logger.error("❌ No valid embeddings found!")
            return None, 0
        
        embeddings = np.array(embeddings_list, dtype='float32')
        logger.success(f"✓ Extracted {len(embeddings_list)} embeddings (dimension {dimension_target})")
        
        # Build FAISS index
        logger.info("🏗️  Building FAISS index...")
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)
        
        # Ensure directory exists
        faiss_dir.mkdir(parents=True, exist_ok=True)
        
        # Save FAISS index
        logger.info(f"💾 Saving index to {index_path}")
        faiss.write_index(index, str(index_path))
        
        # Save mapping from FAISS position to embedding_id
        mapping_path = faiss_dir / "embedding_id_mapping.npy"
        np.save(str(mapping_path), np.array(embedding_ids, dtype='int32'))
        
        logger.success("✓ FAISS index rebuilt successfully!")
        logger.info(f"  📏 Index type: IndexFlatL2")
        logger.info(f"  📐 Dimension: {dimension}")
        logger.info(f"  📊 Total vectors: {index.ntotal}")
        logger.info(f"  🗺️  Mapping: {mapping_path.name}")
        logger.info(f"  📂 Location: {index_path}")
        
        return index_path, index.ntotal
        
    except Exception as e:
        logger.error(f"❌ Failed to rebuild FAISS index: {e}")
        raise
    finally:
        db.close()


def main():
    """Main entry point for standalone execution"""
    logger.header("FAISS INDEX REBUILD")
    
    try:
        index_path, total = rebuild_faiss_index()
        
        if index_path:
            logger.header("✓ REBUILD COMPLETE!")
            logger.info(f"Index saved: {index_path}")
            logger.info(f"Total vectors: {total}")
        else:
            logger.error("❌ Rebuild failed - no segments found")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Rebuild failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
