"""
Search service using FAISS
"""
import numpy as np
import faiss
from typing import List, Dict

from app.config.settings import settings
from app.db.session import get_db_session
from app.db.models import NerdcastSegment
from app.services.embedding_service import EmbeddingService
from app.utils.text_utils import truncate_text
from app.utils.logger import logger


class SearchService:
    """Handles semantic search using FAISS"""
    
    def __init__(self):
        """Initialize search service"""
        self.embedding_service = EmbeddingService()
        self.index = None
        self.index_path = str(settings.get_faiss_index_path())
        self.load_index()
    
    def load_index(self):
        """Load FAISS index from disk"""
        index_path = settings.get_faiss_index_path()
        
        if index_path.exists():
            logger.info(f"Loading FAISS index from {index_path}")
            self.index = faiss.read_index(str(index_path))
            logger.success(f"Index loaded. Total vectors: {self.index.ntotal}")
        else:
            logger.warning(f"FAISS index not found at {index_path}")
            logger.warning("Run the ingestion script first to build the index")
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
            for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
                if idx == -1:  # FAISS returns -1 for empty slots
                    continue
                
                # Get segment from database by embedding_id
                segment = db.query(NerdcastSegment).filter(
                    NerdcastSegment.embedding_id == int(idx)
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
