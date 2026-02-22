"""
Utility functions for extracting program information from podcast metadata
"""
import re
from typing import Optional


def extract_program_from_title(title: str) -> Optional[str]:
    """
    Extract program name from episode title.
    
    Works for feeds that contain multiple programs (like Jovem Nerd feed).
    
    Args:
        title: Episode title from RSS feed
        
    Returns:
        Program name or None if cannot be determined
        
    Examples:
        "NerdCast 1018 - Topic" -> "NerdCast"
        "NerdTech 116 - Topic" -> "NerdTech"
        "Nerd na Cloud 22 - Topic" -> "Nerd na Cloud"
        "Vai te Catar - Topic" -> "Vai te Catar"
    """
    if not title:
        return None
    
    title_lower = title.lower()
    
    # Order matters: check more specific patterns first
    
    # Nerdcast variations
    if 'nerdcast empreendedor' in title_lower or 'empreendedor' in title_lower:
        return 'NerdCast Empreendedor'
    
    if 'nerdcast ciência' in title_lower or 'nerdcast cientista' in title_lower:
        return 'NerdCast Ciência'
    
    if 'nerdcast' in title_lower:
        return 'NerdCast'
    
    # Other programs from Jovem Nerd
    if 'nerdtech' in title_lower or 'nerd tech' in title_lower:
        return 'NerdTech'
    
    if 'nerd na cloud' in title_lower:
        return 'Nerd na Cloud'
    
    if 'vai te catar' in title_lower:
        return 'Vai te Catar'
    
    if 'lá do bunker' in title_lower or 'la do bunker' in title_lower or 'bunker' in title_lower:
        return 'Lá do Bunker'
    
    if 'nerdoffice' in title_lower or 'nerd office' in title_lower:
        return 'NerdOffice'
    
    # If no specific program identified, try to extract from pattern "ProgramName Number - Title"
    # Example: "SomePodcast 123 - Episode Title"
    match = re.match(r'^([A-Za-z\s]+)\s+\d', title)
    if match:
        program = match.group(1).strip()
        if len(program) > 3:  # Need meaningful name
            return program.title()
    
    # Default: unknown program
    return None


def normalize_program_name(program: Optional[str], feed_source: str = 'nerdcast') -> str:
    """
    Normalize program name or provide default based on feed source.
    
    Args:
        program: Extracted program name (can be None)
        feed_source: Feed source identifier
        
    Returns:
        Normalized program name
    """
    if program:
        return program
    
    # Defaults per feed
    if feed_source == 'nerdcast' or feed_source == 'jovem_nerd':
        return 'NerdCast'
    
    return 'Unknown'
