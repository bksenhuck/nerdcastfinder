"""
Text processing utilities
"""
from typing import List


def split_text_into_chunks(text: str, chunk_size: int = 750) -> List[str]:
    """
    Split text into chunks of approximately chunk_size characters.
    Tries to split on sentence boundaries when possible.
    
    Args:
        text: Full text to split
        chunk_size: Target size for each chunk in characters
        
    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    
    # Split on sentence boundaries
    sentences = text.replace("! ", "!|").replace("? ", "?|").replace(". ", ".|").split("|")
    
    current_chunk = ""
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
    
    # Add the last chunk
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length, adding a suffix if truncated.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + suffix


def clean_text(text: str) -> str:
    """
    Clean text by removing extra whitespace and normalizing.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    # Remove extra whitespace
    text = " ".join(text.split())
    return text.strip()
