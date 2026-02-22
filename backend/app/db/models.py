"""
Database models for Podcast Finder (multi-podcast support)
"""
import numpy as np
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, LargeBinary, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PodcastEpisode(Base):
    """
    Stores metadata about podcast episodes from multiple podcasts
    """
    __tablename__ = "podcast_episodes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    podcast_source = Column(String(100), nullable=False, index=True, default='nerdcast')  # Feed source (ex: "jovem_nerd")
    program_name = Column(String(100), nullable=True, index=True)  # Program within feed (ex: "NerdCast", "NerdTech")
    filename = Column(String(255), nullable=False, unique=True, index=True)  # Chave: nome tratado
    title_original = Column(String(500), nullable=False)  # Nome original do RSS
    summary = Column(Text, nullable=True)  # Descrição do episódio
    image_url = Column(Text, nullable=True)  # URL da imagem/capa do episódio
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
            f"<PodcastEpisode(podcast_source='{self.podcast_source}', "
            f"filename='{self.filename}', "
            f"title='{self.title_original[:50]}', "
            f"size={self.file_size_mb}MB)>"
        )


class PodcastSegment(Base):
    """
    Stores podcast episode segments with their text content and embeddings
    Supports multiple podcasts via podcast_source field
    """
    __tablename__ = "podcast_segments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    podcast_source = Column(String(100), nullable=False, index=True, default='nerdcast')  # Identifica qual podcast
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
            f"<PodcastSegment(id={self.id}, "
            f"podcast_source='{self.podcast_source}', "
            f"episode='{self.episode}', "
            f"embedding_id={self.embedding_id})>"
        )


# Backward compatibility aliases
# TODO: Remove these after all code has been updated to use new names
NerdcastEpisode = PodcastEpisode
NerdcastSegment = PodcastSegment
