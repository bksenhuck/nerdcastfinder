"""
Database models for Nerdcast Finder
"""
import numpy as np
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, LargeBinary, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class NerdcastEpisode(Base):
    """
    Stores metadata about podcast episodes
    """
    __tablename__ = "nerdcast_episodes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False, unique=True, index=True)  # Chave: nome tratado
    title_original = Column(String(500), nullable=False)  # Nome original do RSS
    published_date = Column(DateTime, nullable=True)  # Data de publicação
    duration_seconds = Column(Integer, nullable=True)  # Duração em segundos
    file_size_mb = Column(Float, nullable=True)  # Tamanho do arquivo em MB
    audio_url = Column(Text, nullable=True)  # URL do áudio original
    status = Column(String(50), default="downloaded")  # downloaded, transcribed, indexed
    downloaded_at = Column(DateTime, nullable=True)  # Última vez que o arquivo foi baixado
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return (
            f"<NerdcastEpisode(filename='{self.filename}', "
            f"title='{self.title_original[:50]}', "
            f"size={self.file_size_mb}MB)>"
        )


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
