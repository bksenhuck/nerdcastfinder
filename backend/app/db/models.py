"""
Database models for Nerdcast Finder
"""
import numpy as np
from sqlalchemy import Column, Integer, String, Text, LargeBinary
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class NerdcastSegment(Base):
    """
    Stores podcast episode segments with their text content and embeddings
    """
    __tablename__ = "nerdcast_segments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    episode = Column(String(500), nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding_id = Column(Integer, nullable=False, unique=True, index=True)
    embedding = Column(LargeBinary, nullable=True)  # Stores numpy array as bytes
    
    def set_embedding(self, embedding_array: np.ndarray):
        """Convert numpy array to bytes for storage"""
        self.embedding = embedding_array.astype('float32').tobytes()
    
    def get_embedding(self) -> np.ndarray:
        """Convert bytes back to numpy array"""
        if self.embedding is None:
            return None
        return np.frombuffer(self.embedding, dtype='float32')
    
    def __repr__(self):
        return (
            f"<NerdcastSegment(id={self.id}, "
            f"episode='{self.episode}', "
            f"embedding_id={self.embedding_id})>"
        )
