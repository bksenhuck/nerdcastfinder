"""
Transcription service using Whisper
"""
from typing import List
from dataclasses import dataclass
import whisper
from pathlib import Path

from app.config.settings import settings
from app.utils.text_utils import split_text_into_chunks
from app.utils.file_utils import find_audio_files, get_episode_name
from app.utils.logger import logger


@dataclass
class TranscriptChunk:
    """Represents a chunk of transcribed text"""
    episode_name: str
    chunk_text: str


class TranscriptionService:
    """Handles audio transcription using Whisper"""
    
    def __init__(
        self,
        model_name: str = None,
        chunk_size: int = None,
        language: str = None
    ):
        """
        Initialize transcription service
        
        Args:
            model_name: Whisper model to use (default: from settings)
            chunk_size: Target size for text chunks in characters
                (default: from settings)
            language: Transcription language (default: from settings)
        """
        self.model_name = model_name or settings.WHISPER_MODEL
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.language = language or settings.TRANSCRIPTION_LANGUAGE
        self.model = None
        
    def load_model(self):
        """Load Whisper model (lazy loading)"""
        if self.model is None:
            device = settings.WHISPER_DEVICE
            logger.info(f"Loading Whisper model: {self.model_name} on {device}...")
            self.model = whisper.load_model(self.model_name, device=device)
            logger.success(f"Model loaded successfully on {device}")
    
    def transcribe_audio(self, audio_path: str) -> str:
        """
        Transcribe audio file to text
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Full transcript text
        """
        self.load_model()
        logger.info(f"Transcribing: {Path(audio_path).name}")
        
        result = self.model.transcribe(
            audio_path,
            language=self.language,
            verbose=settings.WHISPER_VERBOSE
        )
        
        return result["text"]
    
    def split_into_chunks(self, text: str) -> List[str]:
        """
        Split text into chunks of approximately chunk_size characters
        
        Args:
            text: Full text to split
            
        Returns:
            List of text chunks
        """
        return split_text_into_chunks(text, self.chunk_size)
    
    def process_audio_file(self, audio_path: str) -> List[TranscriptChunk]:
        """
        Process a single audio file: transcribe and chunk
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            List of TranscriptChunk objects
        """
        episode_name = get_episode_name(audio_path)
        
        # Transcribe
        transcript = self.transcribe_audio(audio_path)
        
        # Split into chunks
        chunks = self.split_into_chunks(transcript)
        
        # Create TranscriptChunk objects
        return [
            TranscriptChunk(episode_name=episode_name, chunk_text=chunk)
            for chunk in chunks
        ]
    
    def process_directory(self, podcasts_dir: str) -> List[TranscriptChunk]:
        """
        Process all audio files in a directory
        
        Args:
            podcasts_dir: Directory containing audio files
            
        Returns:
            List of all TranscriptChunk objects from all files
        """
        all_chunks = []
        
        # Find audio files
        audio_files = find_audio_files(
            Path(podcasts_dir),
            settings.SUPPORTED_AUDIO_EXTENSIONS
        )
        
        logger.info(f"Found {len(audio_files)} audio files to process")
        
        for i, audio_file in enumerate(audio_files, 1):
            try:
                logger.progress(
                    i, len(audio_files), f"Processing {audio_file.name}"
                )
                chunks = self.process_audio_file(str(audio_file))
                all_chunks.extend(chunks)
                logger.success(f"{audio_file.name}: {len(chunks)} chunks")
            except Exception as e:
                logger.error(f"Failed to process {audio_file.name}: {e}")
        
        return all_chunks
