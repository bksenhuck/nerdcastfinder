"""
Text processing utilities
"""
from typing import List


def split_text_into_chunks(text: str, chunk_size: int = 750, overlap: int = 150) -> List[str]:
    """
    Split text into chunks of approximately chunk_size characters with overlap.

    Overlap ensures that content near chunk boundaries appears in two adjacent
    chunks, so semantic search finds relevant passages regardless of where the
    split falls.

    Args:
        text: Full text to split
        chunk_size: Target size for each chunk in characters
        overlap: Characters from the end of the previous chunk to carry into
                 the next one (0 = no overlap)

    Returns:
        List of text chunks
    """
    if len(text) <= chunk_size:
        return [text]

    # Split on sentence boundaries
    sentences = text.replace("! ", "!|").replace("? ", "?|").replace(". ", ".|").split("|")

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # Start next chunk with tail of previous chunk (overlap window)
            if overlap > 0 and current_chunk:
                tail = current_chunk[-overlap:]
                current_chunk = tail + sentence
            else:
                current_chunk = sentence

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
