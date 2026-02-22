"""
Centralized configuration settings for Nerdcast Finder
"""
import os
from pathlib import Path
from typing import Set


class Settings:
    """Application settings and configuration"""
    
    # ===== Model Configuration =====
    WHISPER_MODEL: str = "medium"  # Options: tiny, base, small, medium, large-v3 | medium = 6x faster, ~95% accuracy
    WHISPER_DEVICE: str = "cuda"  # "cuda" for GPU, "cpu" for CPU
    # RTX 5070 now supported with PyTorch 2.10.0 + CUDA 12.8!
    
    # Embedding models (tradeoff between speed and quality):
    # - "all-MiniLM-L6-v2": Small, fast (384 dims)
    # - "all-MiniLM-L12-v2": Medium, balanced (384 dims)
    # - "all-mpnet-base-v2": Large, best quality (768 dims) - slower but more accurate
    EMBEDDING_MODEL: str = "all-mpnet-base-v2"
    
    # ===== Transcription Settings =====
    CHUNK_SIZE: int = 750  # Target characters per chunk
    TRANSCRIPTION_LANGUAGE: str = "pt"  # Portuguese for Nerdcast
    WHISPER_VERBOSE: bool = False
    
    # ===== Embedding Settings =====
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_SHOW_PROGRESS: bool = True
    
    # ===== Search Settings =====
    DEFAULT_TOP_K: int = 10
    MAX_TOP_K: int = 50
    EXCERPT_MAX_LENGTH: int = 500
    
    # ===== Audio File Settings =====
    SUPPORTED_AUDIO_EXTENSIONS: Set[str] = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
    
    # ===== Podcast Download Settings =====
    # Dictionary of podcast name -> RSS feed URL
    PODCASTS: dict = {
        "nerdcast": {
            "name": "Nerdcast",
            "feed_url": "https://jovemnerd.com.br/feed-nerdcast/",
            "description": "O podcast original que deu origem ao projeto"
        },
        "pelada_na_net": {
            "name": "Pelada na Net",
            "feed_url": "https://www.omnycontent.com/d/playlist/f7f86f6a-2fbd-4ac7-ab53-b01900e5d187/2f120fb0-f8eb-43ca-8e9d-b08a00f7ee41/f56245dd-a097-4ef9-b675-b08a00f7ee7e/podcast.rss",
            "description": "Pelada na Net"
        },
    }
    
    DOWNLOAD_TIMEOUT: int = 300  # 5 minutes per episode
    DOWNLOAD_CHUNK_SIZE: int = 8192  # 8KB chunks for streaming
    DOWNLOAD_MAX_RETRIES: int = 3
    DOWNLOAD_BACKOFF_FACTOR: int = 1  # Wait 1s, 2s, 4s between retries
    DOWNLOAD_MAX_CONCURRENT: int = 2  # Max parallel downloads
    
    # ===== Path Configuration =====
    @staticmethod
    def get_backend_dir() -> Path:
        """Get the backend root directory"""
        return Path(__file__).parent.parent.parent
    
    @staticmethod
    def get_data_dir() -> Path:
        """Get the data directory"""
        data_dir = Settings.get_backend_dir() / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    
    @staticmethod
    def get_podcasts_dir(podcast_name: str = None) -> Path:
        """Get the podcasts directory
        
        Args:
            podcast_name: Name of specific podcast (e.g., 'nerdcast'). If None, returns base podcasts dir.
        
        Returns:
            Path to podcast directory
        """
        podcasts_dir = Settings.get_data_dir() / "podcasts"
        
        if podcast_name:
            # Create subdirectory for specific podcast
            podcast_dir = podcasts_dir / podcast_name
            podcast_dir.mkdir(parents=True, exist_ok=True)
            return podcast_dir
        else:
            # Return base podcasts directory
            podcasts_dir.mkdir(parents=True, exist_ok=True)
            return podcasts_dir
    
    @staticmethod
    def get_faiss_dir() -> Path:
        """Get the FAISS index directory"""
        faiss_dir = Settings.get_data_dir() / "faiss_index"
        faiss_dir.mkdir(parents=True, exist_ok=True)
        return faiss_dir
    
    @staticmethod
    def get_faiss_index_path() -> Path:
        """Get the FAISS index file path"""
        return Settings.get_faiss_dir() / "nerdcast.index"
    
    @staticmethod
    def get_database_path() -> Path:
        """Get the SQLite database path"""
        return Settings.get_data_dir() / "nerdcasts.db"
    
    @staticmethod
    def get_database_url() -> str:
        """Get the SQLAlchemy database URL"""
        return f"sqlite:///{Settings.get_database_path()}"
    
    # ===== Database Settings =====
    DB_ECHO: bool = False  # Set to True for SQL debug logging
    DB_CHECK_SAME_THREAD: bool = False  # For SQLite
    
    # ===== API Settings =====
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = False  # Disabled to force clean restart
    API_TITLE: str = "Nerdcast Finder API"
    API_DESCRIPTION: str = "Semantic search API for podcast episodes"
    API_VERSION: str = "1.0.0"
    
    # ===== CORS Settings =====
    CORS_ALLOW_ORIGINS: list = ["*"]  # Restrict in production
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]


# Create a singleton instance
settings = Settings()
