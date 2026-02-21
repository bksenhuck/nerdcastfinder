"""
File system utilities
"""
from pathlib import Path
from typing import List, Set


def find_audio_files(
    directory: Path,
    extensions: Set[str] = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
) -> List[Path]:
    """
    Find all audio files in a directory.
    
    Args:
        directory: Directory to search
        extensions: Set of valid audio file extensions
        
    Returns:
        List of paths to audio files
    """
    directory = Path(directory)
    
    if not directory.exists():
        raise FileNotFoundError(f"Directory not found: {directory}")
    
    if not directory.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")
    
    audio_files = [
        f for f in directory.iterdir()
        if f.is_file() and f.suffix.lower() in extensions
    ]
    
    return sorted(audio_files)


def get_episode_name(file_path: Path) -> str:
    """
    Extract episode name from audio file path.
    
    Args:
        file_path: Path to audio file
        
    Returns:
        Episode name (filename without extension)
    """
    return Path(file_path).stem


def ensure_directory_exists(directory: Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Directory path
        
    Returns:
        The directory path
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return directory
