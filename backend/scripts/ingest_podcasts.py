"""
Ingestion script for Nerdcast Finder

This script:
1. Transcribes podcast audio files using Whisper
2. Generates embeddings for each chunk
3. Stores segments in SQLite database
4. Builds/updates FAISS index for search

Usage:
    python -m backend.scripts.ingest_podcasts
"""
import sys
import numpy as np
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config.settings import settings
from app.services.transcription_service import TranscriptionService
from app.services.embedding_service import EmbeddingService
from app.db.session import init_db, get_db_session
from app.db.models import NerdcastSegment
from app.utils.logger import logger

# Import shared rebuild function
from backend.scripts.rebuild_faiss_index import rebuild_faiss_index


class PodcastIngestionPipeline:
    """Orchestrates the entire ingestion pipeline"""
  
    def __init__(self, podcasts_dir: str = None):
        """
        Initialize the ingestion pipeline
        
        Args:
            podcasts_dir: Directory containing podcast audio files (default: from settings)
        """
        self.podcasts_dir = podcasts_dir or str(settings.get_podcasts_dir())
        self.transcription_service = TranscriptionService()
        self.embedding_service = EmbeddingService()
    
    def run(self):
        """Execute the full ingestion pipeline"""
        logger.header("NERDCAST FINDER - INGESTION PIPELINE")
        
        # Step 1: Initialize database
        logger.section("[1/5] Initializing database...")
        init_db()
        logger.success("Database initialized")
        
        # Step 2: Find audio files
        logger.section(f"[2/5] Scanning {self.podcasts_dir}...")
        from app.utils.file_utils import find_audio_files
        audio_files = find_audio_files(
            Path(self.podcasts_dir),
            settings.SUPPORTED_AUDIO_EXTENSIONS
        )
        
        if not audio_files:
            logger.error("No audio files found. Exiting.")
            return
        
        logger.success(f"Found {len(audio_files)} audio files to process")
        
        # Step 3: Process each podcast incrementally
        logger.section(f"[3/5] Processing podcasts (incremental)...")
        total_segments = 0
        
        for i, audio_file in enumerate(audio_files, 1):
            try:
                logger.info(f"[{i}/{len(audio_files)}] Processing {audio_file.name}")
                
                # Transcribe this file
                chunks = self.transcription_service.process_audio_file(str(audio_file))
                logger.success(f"  Transcribed: {len(chunks)} chunks")
                
                # Generate embeddings for this file
                chunk_texts = [chunk.chunk_text for chunk in chunks]
                embeddings = self.embedding_service.generate_embeddings(chunk_texts)
                logger.success(f"  Generated: {len(embeddings)} embeddings")
                
                # Store in database with embeddings
                episode_name = chunks[0].episode_name
                segment_count = self._store_episode_to_db(episode_name, chunks, embeddings)
                total_segments += segment_count
                logger.success(f"  Stored: {segment_count} segments in DB")
                
            except Exception as e:
                logger.error(f"Failed to process {audio_file.name}: {e}")
                logger.warning("Continuing with next file...")
                continue
        
        logger.success(f"Processed {len(audio_files)} files, {total_segments} total segments")
        
        # Step 4: Rebuild FAISS index from database
        logger.section("[4/5] Rebuilding FAISS index from database...")
        index_path, total_vectors = rebuild_faiss_index()
        if index_path:
            logger.success(f"FAISS index built: {total_vectors} vectors")
        else:
            logger.warning("FAISS index rebuild failed (no segments)")
        
        logger.header("INGESTION COMPLETE!")
        logger.info(f"Total segments indexed: {total_segments}")
    
    def _store_episode_to_db(self, episode_name: str, chunks: list, embeddings: np.ndarray) -> int:
        """
        Store episode chunks and embeddings in database (with merge strategy)
        
        Args:
            episode_name: Name of the episode
            chunks: List of TranscriptChunk objects
            embeddings: numpy array of embeddings
            
        Returns:
            Number of segments stored
        """
        db = get_db_session()
        stored_count = 0
        
        try:
            # Delete all existing segments for this episode (merge strategy)
            deleted_count = db.query(NerdcastSegment).filter(
                NerdcastSegment.episode == episode_name
            ).delete()
            
            if deleted_count > 0:
                logger.info(f"  Removed {deleted_count} old segments for '{episode_name}'")
            
            # Insert new segments with embeddings
            for idx, chunk in enumerate(chunks):
                # Generate global embedding_id (unique across all episodes)
                # Use timestamp-based or hash-based ID to avoid collisions
                embedding_id = hash(f"{episode_name}_{idx}") % (2**31)
                
                segment = NerdcastSegment(
                    episode=episode_name,
                    content=chunk.chunk_text,
                    embedding_id=embedding_id
                )
                segment.set_embedding(embeddings[idx])
                db.add(segment)
                stored_count += 1
            
            db.commit()
            
        except Exception as e:
            db.rollback()
            logger.error(f"Database error for '{episode_name}': {e}")
            raise
        finally:
            db.close()
        
        return stored_count


def main():
    """Main entry point"""
    # Get podcasts directory from settings
    podcasts_dir = settings.get_podcasts_dir()
    
    if not podcasts_dir.exists():
        logger.error(f"Podcasts directory not found: {podcasts_dir}")
        logger.info("Please run download_podcasts.py first to download audio files")
        return
    
    pipeline = PodcastIngestionPipeline(str(podcasts_dir))
    pipeline.run()


if __name__ == "__main__":
    main()
