"""
Search service using FAISS
"""
import logging
import numpy as np
import faiss
from typing import List, Dict

from app.config.settings import settings
from app.db.session import get_db_session
from app.db.models import NerdcastSegment
from app.services.embedding_service import EmbeddingService
from app.utils.text_utils import truncate_text
from app.utils.logger import logger

# Setup logging for uvicorn
log = logging.getLogger("uvicorn.error")


class SearchService:
    """Handles semantic search using FAISS"""
    
    def __init__(self):
        """Initialize search service"""
        # Use CPU for search (frontend use) to ensure stable performance
        self.embedding_service = EmbeddingService(force_cpu=True)
        self.index = None
        self.embedding_id_mapping = None  # Maps FAISS position to embedding_id
        self.index_path = str(settings.get_faiss_index_path())
        self.load_index()
    
    def load_index(self):
        """Load FAISS index and mapping from disk"""
        index_path = settings.get_faiss_index_path()
        
        log.info("=" * 60)
        log.info("Loading FAISS Index...")
        log.info("=" * 60)
        log.info(f"Index path: {index_path}")
        log.info(f"Index exists: {index_path.exists()}")
        
        logger.section("Loading FAISS Index...")
        logger.info(f"Index path: {index_path}")
        logger.info(f"Index exists: {index_path.exists()}")
        
        if index_path.exists():
            try:
                self.index = faiss.read_index(str(index_path))
                log.info(f"✓ FAISS index loaded successfully")
                log.info(f"  Total vectors: {self.index.ntotal}")
                logger.success(f"✓ FAISS index loaded successfully")
                logger.info(f"  Total vectors: {self.index.ntotal}")
                
                # Load embedding_id mapping
                mapping_path = settings.get_faiss_dir() / "embedding_id_mapping.npy"
                log.info(f"Mapping path: {mapping_path}")
                log.info(f"Mapping exists: {mapping_path.exists()}")
                logger.info(f"Mapping path: {mapping_path}")
                logger.info(f"Mapping exists: {mapping_path.exists()}")
                
                if mapping_path.exists():
                    self.embedding_id_mapping = np.load(str(mapping_path))
                    log.info(f"✓ Embedding ID mapping loaded successfully")
                    log.info(f"  Total mappings: {len(self.embedding_id_mapping)}")
                    logger.success(f"✓ Embedding ID mapping loaded successfully")
                    logger.info(f"  Total mappings: {len(self.embedding_id_mapping)}")
                else:
                    log.error(f"✗ Mapping file not found at {mapping_path}")
                    log.warning("Search may not work correctly. Re-run ingestion script.")
                    logger.error(f"✗ Mapping file not found at {mapping_path}")
                    logger.warning("Search may not work correctly. Re-run ingestion script.")
                    self.index = None
            except Exception as e:
                log.error(f"✗ Failed to load FAISS index: {e}")
                logger.error(f"✗ Failed to load FAISS index: {e}")
                self.index = None
        else:
            log.error(f"✗ FAISS index not found at {index_path}")
            log.warning("⚠️  Run the ingestion script first to build the index")
            log.info("Command: python -m backend.scripts.ingest_podcasts")
            logger.error(f"✗ FAISS index not found at {index_path}")
            logger.warning("⚠️  Run the ingestion script first to build the index")
            logger.info("Command: python -m backend.scripts.ingest_podcasts")
            self.index = None
    
    def search(self, query: str, top_k: int = None) -> List[Dict]:
        """
        Search for similar segments
        
        Args:
            query: Search query string
            top_k: Number of results to return (default: from settings)
            
        Returns:
            List of dicts with keys: episode, excerpt, score
        """
        if self.index is None:
            raise RuntimeError("FAISS index not loaded. Run ingestion first.")
        
        if self.embedding_id_mapping is None:
            raise RuntimeError("Embedding ID mapping not loaded. Re-run ingestion script.")
        
        top_k = top_k or settings.DEFAULT_TOP_K
        
        # Generate query embedding
        query_embedding = self.embedding_service.generate_embedding(query)
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # Search FAISS index
        distances, indices = self.index.search(query_embedding, top_k)
        
        # Map indices to database rows
        results = []
        db = get_db_session()
        
        try:
            for i, (distance, faiss_idx) in enumerate(zip(distances[0], indices[0])):
                if faiss_idx == -1:  # FAISS returns -1 for empty slots
                    continue
                
                # Map FAISS index to embedding_id
                embedding_id = int(self.embedding_id_mapping[faiss_idx])
                
                # Get segment from database by embedding_id
                segment = db.query(NerdcastSegment).filter(
                    NerdcastSegment.embedding_id == embedding_id
                ).first()
                
                if segment:
                    # Convert distance to similarity score (lower distance = higher similarity)
                    # L2 distance to similarity: use inverse
                    similarity_score = 1 / (1 + float(distance))
                    
                    results.append({
                        "episode": segment.episode,
                        "excerpt": truncate_text(segment.content, settings.EXCERPT_MAX_LENGTH),
                        "score": round(similarity_score, 4)
                    })
        finally:
            db.close()
        
        return results
