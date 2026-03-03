"""
Database models for Podcast Finder (multi-podcast support)
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PodcastEpisode(Base):
    """Stores metadata about podcast episodes from multiple podcasts."""

    __tablename__ = "podcast_episodes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    podcast_source = Column(String(100), nullable=False, index=True, default='nerdcast')
    program_name = Column(String(100), nullable=True, index=True)
    filename = Column(String(255), nullable=False, unique=True, index=True)
    title_original = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    published_date = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    file_size_mb = Column(Float, nullable=True)
    audio_url = Column(Text, nullable=True)
    status = Column(String(50), default="downloaded")
    downloaded_at = Column(DateTime, nullable=True)
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
    Stores podcast episode segment text.
    Raw embedding vectors live in embeddings_matrix.npy / embeddings_ids.npy
    (see backend/pipelines/db/migrate_embeddings_to_npy.py).
    """

    __tablename__ = "podcast_segments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    podcast_source = Column(String(100), nullable=False, index=True, default='nerdcast')
    episode = Column(String(500), nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding_id = Column(Integer, nullable=False, unique=True, index=True)

    def __repr__(self):
        return (
            f"<PodcastSegment(id={self.id}, "
            f"podcast_source='{self.podcast_source}', "
            f"episode='{self.episode}', "
            f"embedding_id={self.embedding_id})>"
        )


# Backward compatibility aliases
NerdcastEpisode = PodcastEpisode
NerdcastSegment = PodcastSegment
