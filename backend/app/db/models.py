"""
Database models for Nerdcast Finder
"""
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class NerdcastSegment(Base):
    """
    Stores podcast episode segments with their text content
    """
    __tablename__ = "nerdcast_segments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    episode = Column(String(500), nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding_id = Column(Integer, nullable=False, unique=True, index=True)
    
    def __repr__(self):
        return (
            f"<NerdcastSegment(id={self.id}, "
            f"episode='{self.episode}', "
            f"embedding_id={self.embedding_id})>"
        )
