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
import faiss
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
        
        # Paths from settings
        self.faiss_dir = settings.get_faiss_dir()
        self.index_path = settings.get_faiss_index_path()
    
    def run(self):
        """Execute the full ingestion pipeline"""
        logger.header("NERDCAST FINDER - INGESTION PIPELINE")
        
        # Step 1: Initialize database
        logger.section("[1/5] Initializing database...")
        init_db()
        logger.success("Database initialized")
        
        # Step 2: Transcribe podcasts
        logger.section(f"[2/5] Transcribing podcasts from {self.podcasts_dir}...")
        chunks = self.transcription_service.process_directory(self.podcasts_dir)
        
        if not chunks:
            logger.error("No audio files found or processed. Exiting.")
            return
        
        logger.success(f"Transcribed {len(chunks)} total chunks")
        
        # Step 3: Generate embeddings
        logger.section("[3/5] Generating embeddings...")
        chunk_texts = [chunk.chunk_text for chunk in chunks]
        embeddings = self.embedding_service.generate_embeddings(chunk_texts)
        logger.success(f"Generated {len(embeddings)} embeddings")
        
        # Step 4: Store in database (idempotent)
        logger.section("[4/5] Storing in database...")
        db = get_db_session()
        stored_count = 0
        updated_count = 0
        
        try:
            for i, chunk in enumerate(chunks):
                # Check if this chunk already exists
                existing = db.query(NerdcastSegment).filter(
                    NerdcastSegment.episode == chunk.episode_name,
                    NerdcastSegment.content == chunk.chunk_text
                ).first()
                
                if existing:
                    # Update embedding_id if needed
                    if existing.embedding_id != i:
                        existing.embedding_id = i
                        updated_count += 1
                else:
                    # Create new segment
                    segment = NerdcastSegment(
                        episode=chunk.episode_name,
                        content=chunk.chunk_text,
                        embedding_id=i
                    )
                    db.add(segment)
                    stored_count += 1
            
            db.commit()
            logger.success(f"Database updated: {stored_count} new, {updated_count} updated")
        
        except Exception as e:
            db.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            db.close()
        
        # Step 5: Build FAISS index
        logger.section("[5/5] Building FAISS index...")
        self._build_faiss_index(embeddings)
        logger.success(f"FAISS index built and saved to {self.index_path}")
        
        logger.header("INGESTION COMPLETE!")
        logger.info(f"Total segments indexed: {len(chunks)}")
    
    def _build_faiss_index(self, embeddings: np.ndarray):
        """
        Build and save FAISS index
        
        Args:
            embeddings: Array of embeddings (n_vectors, dimension)
        """
        dimension = embeddings.shape[1]
        
        # Create FAISS index (L2 distance)
        index = faiss.IndexFlatL2(dimension)
        
        # Add embeddings
        embeddings_float32 = embeddings.astype('float32')
        index.add(embeddings_float32)
        
        # Save to disk
        faiss.write_index(index, str(self.index_path))
        
        print(f"  Index type: IndexFlatL2")
        print(f"  Dimension: {dimension}")
        print(f"  Total vectors: {index.ntotal}")

        logger.info(f"  Index type: IndexFlatL2")
        logger.info(f"  Dimension: {dimension}")
        logger.info(f"  Total vectors: {index.ntotal}")


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
