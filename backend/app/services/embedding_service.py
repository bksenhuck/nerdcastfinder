"""
Embedding service using sentence-transformers
"""
import numpy as np
from typing import List
from sentence_transformers import SentenceTransformer
import torch

from app.config.settings import settings
from app.utils.logger import logger


class EmbeddingService:
    """Handles text embedding generation"""
    
    def __init__(self, model_name: str = None, force_cpu: bool = False):
        """
        Initialize embedding service
        
        Args:
            model_name: sentence-transformers model to use
                (default: from settings)
            force_cpu: Force CPU usage (useful for frontend)
        """
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.model = None
        self.embedding_dim = None
        self.force_cpu = force_cpu
        self.device = None
    
    def load_model(self):
        """Load sentence-transformers model (lazy loading)"""
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}...")
            
            # Determine device
            if self.force_cpu:
                device = 'cpu'
                logger.info("✓ Using CPU (forced)")
            else:
                # Try GPU first, fallback to CPU
                if torch.cuda.is_available():
                    try:
                        device = 'cuda'
                        logger.info(
                            f"✓ GPU available: "
                            f"{torch.cuda.get_device_name(0)}"
                        )
                        logger.info("✓ Using GPU for embeddings")
                    except Exception as e:
                        device = 'cpu'
                        logger.warning(
                            f"GPU initialization failed: {e}. "
                            f"Falling back to CPU"
                        )
                        logger.info("✓ Using CPU (GPU fallback)")
                else:
                    device = 'cpu'
                    logger.info("✓ GPU not available, using CPU")
            
            self.device = device
            self.model = SentenceTransformer(self.model_name, device=device)
            self.embedding_dim = (
                self.model.get_sentence_embedding_dimension()
            )
            logger.success(
                f"Model loaded on {device.upper()}. "
                f"Embedding dimension: {self.embedding_dim}"
            )
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text
        
        Args:
            text: Text to embed
            
        Returns:
            Numpy array of embedding vector
        """
        self.load_model()
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding
    
    def generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = None,
        show_progress: bool = None
    ) -> np.ndarray:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing (default: from settings)
            show_progress: Whether to show progress bar
                (default: from settings)
            
        Returns:
            Numpy array of shape (len(texts), embedding_dim)
        """
        self.load_model()
        
        batch_size = batch_size or settings.EMBEDDING_BATCH_SIZE
        show_progress = (
            show_progress if show_progress is not None
            else settings.EMBEDDING_SHOW_PROGRESS
        )
        
        logger.info(f"Generating embeddings for {len(texts)} texts...")
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model"""
        self.load_model()
        return self.embedding_dim
