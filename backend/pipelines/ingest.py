"""
Ingestion script for Podcast Finder

This script:
1. Transcribes podcast audio files using Whisper
2. Generates embeddings for each chunk
3. Stores segments in SQLite database
4. Builds/updates FAISS index for search

Usage:
    python -m backend.pipelines.ingest --list
    python -m backend.pipelines.ingest --podcast nerdcast
    python -m backend.pipelines.ingest --all

Options:
    --list : Show available podcasts
    --podcast NAME : Ingest specific podcast by name
    --all : Ingest all downloaded podcasts
"""
import numpy as np
from pathlib import Path

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.services.transcription_service import TranscriptionService
from backend.app.services.embedding_service import EmbeddingService
from backend.app.db.session import init_db, get_db_session
from backend.app.db.models import PodcastSegment
from backend.pipelines.rebuild_index import rebuild_faiss_index


class PodcastIngestionPipeline:
    """Orchestrates the entire ingestion pipeline"""
  
    def __init__(self, podcast_name: str = None, resume_from: str = None):
        """
        Initialize the ingestion pipeline
        
        Args:
            podcast_name: Name of the podcast to ingest (e.g., 'nerdcast'). 
                         If None, will try to ingest from base podcasts dir.
            resume_from: Episode filename to resume from (e.g., 'lá_do_bunker_150')
        """
        self.podcast_name = podcast_name
        self.resume_from = resume_from
        
        if podcast_name:
            # Check if podcast exists in config
            if podcast_name not in settings.PODCASTS:
                raise ValueError(f"Podcast '{podcast_name}' not found in configuration")
            
            self.podcast_config = settings.PODCASTS[podcast_name]
            self.podcast_display_name = self.podcast_config["name"]
            self.podcasts_dir = settings.get_podcasts_dir(podcast_name)
        else:
            # Legacy mode - base podcasts directory
            self.podcast_display_name = "All Podcasts"
            self.podcasts_dir = settings.get_podcasts_dir()
        
        self.transcription_service = TranscriptionService()
        self.embedding_service = EmbeddingService()
    
    def run(self):
        """Execute the full ingestion pipeline"""
        logger.header(f"INGESTION: {self.podcast_display_name}")
        
        # Step 1: Initialize database
        logger.section("[1/5] Initializing database...")
        init_db()
        logger.success("Database initialized")
        
        # Step 2: Find audio files
        logger.section(f"[2/5] Scanning {self.podcasts_dir}...")
        from backend.app.utils.file_utils import find_audio_files
        audio_files = find_audio_files(
            Path(self.podcasts_dir),
            settings.SUPPORTED_AUDIO_EXTENSIONS
        )
        
        if not audio_files:
            logger.error(f"No audio files found in {self.podcasts_dir}")
            logger.info("Please run download script first to download audio files")
            return False
        
        logger.success(f"Found {len(audio_files)} audio files to process")
        
        # Handle resume_from
        start_idx = 0
        if self.resume_from:
            logger.info(
                f"⏭️  Resuming from: {self.resume_from}"
            )
            for idx, audio_file in enumerate(audio_files):
                file_base = audio_file.stem
                if self.resume_from in file_base:
                    start_idx = idx
                    logger.success(
                        f"Found episode at index {idx + 1}"
                    )
                    break
            else:
                logger.warning(
                    f"Episode '{self.resume_from}' not found"
                )
        
        # Step 3: Process each podcast incrementally
        logger.section(f"[3/5] Processing podcasts (incremental)...")
        total_segments = 0
        audio_files_to_process = audio_files[start_idx:]
        skipped = len(audio_files) - len(audio_files_to_process)
        
        if skipped > 0:
            logger.info(f"⏭️  Skipped {skipped} episodes")
        
        for i, audio_file in enumerate(
            audio_files_to_process,
            start=start_idx + 1
        ):
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
        return True
    
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
            deleted_count = db.query(PodcastSegment).filter(
                PodcastSegment.episode == episode_name,
                PodcastSegment.podcast_source == self.podcast_name
            ).delete()
            
            if deleted_count > 0:
                logger.info(f"  Removed {deleted_count} old segments for '{episode_name}'")
            
            # Insert new segments with embeddings
            for idx, chunk in enumerate(chunks):
                # Generate global embedding_id (unique across all episodes)
                # Use timestamp-based or hash-based ID to avoid collisions
                embedding_id = hash(f"{self.podcast_name}_{episode_name}_{idx}") % (2**31)
                
                segment = PodcastSegment(
                    podcast_source=self.podcast_name,
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


def main(
    podcast_name: str = None,
    resume_from: str = None
):
    """Main entry point
    
    Args:
        podcast_name: Name of the podcast to ingest (e.g., 'nerdcast').
                      If None, uses base dir.
        resume_from: Episode filename to resume from.
        
    Returns:
        True if successful, False otherwise
    """
    try:
        pipeline = PodcastIngestionPipeline(
            podcast_name,
            resume_from=resume_from
        )
        return pipeline.run()
    except ValueError as e:
        logger.error(str(e))
        logger.info("Use --list to see available podcasts")
        return False
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        return False


def ingest_all_podcasts():
    """Ingest all configured podcasts
    
    Returns:
        True if all succeeded, False if any failed
    """
    logger.header("📖 INGEST ALL PODCASTS")
    
    podcasts = settings.PODCASTS
    total_podcasts = len(podcasts)
    failed_podcasts = []
    
    for idx, (podcast_id, podcast_config) in enumerate(podcasts.items(), 1):
        podcast_name = podcast_config["name"]
        logger.section(f"[{idx}/{total_podcasts}] {podcast_name}")
        
        success = main(podcast_name=podcast_id)
        
        if not success:
            failed_podcasts.append(podcast_name)
        
        # Pequena pausa entre podcasts
        if idx < total_podcasts:
            import time
            time.sleep(2)
    
    # Summary
    logger.header("📊 RESUMO GERAL")
    logger.success(f"✓ Processados: {total_podcasts} podcasts")
    
    if failed_podcasts:
        logger.error(f"❌ Falharam: {len(failed_podcasts)}")
        for name in failed_podcasts:
            logger.error(f"  - {name}")
        return False
    else:
        logger.success("✓ Todos os podcasts ingeridos com sucesso!")
        return True


def list_podcasts():
    """List all available podcasts"""
    logger.header("📻 PODCASTS DISPONÍVEIS")
    
    podcasts = settings.PODCASTS
    
    if not podcasts:
        logger.warning("Nenhum podcast configurado")
        return
    
    logger.info(f"Total: {len(podcasts)} podcast(s) configurado(s)\n")
    
    for podcast_id, config in podcasts.items():
        podcast_dir = settings.get_podcasts_dir(podcast_id)
        
        # Check if directory exists and has audio files
        from backend.app.utils.file_utils import find_audio_files
        audio_count = 0
        if podcast_dir.exists():
            audio_files = find_audio_files(podcast_dir, settings.SUPPORTED_AUDIO_EXTENSIONS)
            audio_count = len(audio_files)
        
        logger.info(f"🎙️  {config['name']}")
        logger.info(f"   ID: {podcast_id}")
        logger.info(f"   Diretório: {podcast_dir}")
        logger.info(f"   Arquivos de áudio: {audio_count}")
        if 'description' in config:
            logger.info(f"   Descrição: {config['description']}")
        logger.info("")  # Blank line
    
    logger.info("Uso:")
    logger.info("  python -m backend.pipelines.ingest --podcast <ID>")
    logger.info("  python -m backend.pipelines.ingest --podcast <ID> --resume-from <EPISODE>")
    logger.info("  python -m backend.pipelines.ingest --all")


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Ingest podcast audio files to build search index"
    )
    
    # Mutually exclusive group for podcast selection
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--list',
        action='store_true',
        help='List all available podcasts'
    )
    group.add_argument(
        '--podcast',
        type=str,
        metavar='NAME',
        help='Ingest specific podcast by name'
    )
    group.add_argument(
        '--all',
        action='store_true',
        help='Ingest all downloaded podcasts'
    )
    
    # Optional resume argument
    parser.add_argument(
        '--resume-from',
        type=str,
        metavar='EPISODE',
        help='Resume ingestion from specific episode (e.g., --resume-from lá_do_bunker_150)'
    )
    
    args = parser.parse_args()
    
    # Handle --list
    if args.list:
        list_podcasts()
        sys.exit(0)
    
    # Handle --all
    if args.all:
        success = ingest_all_podcasts()
        sys.exit(0 if success else 1)
    
    # Handle --podcast
    if args.podcast:
        success = main(
            podcast_name=args.podcast,
            resume_from=args.resume_from
        )
        sys.exit(0 if success else 1)
    
    # No arguments provided - show help
    parser.print_help()
    logger.info("\nDica: Use --list para ver podcasts disponíveis")
    sys.exit(1)
