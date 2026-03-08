"""
Path utilities for safe logging and display.

This module centralizes path formatting so callers can log
relative or filename-only values without exposing absolute
filesystem paths.
"""
import re
from pathlib import Path
from typing import Union


def get_stable_id(filename: str, podcast_source: str) -> str:
    """
    Generates a stable identifier for a podcast episode.
    Pattern: [podcast_source]_[episode_number]
    Example: nerdcast_454, nerdcast_100a, pelada_na_net_454
    """
    if not filename:
        return ""
    
    # Remove path and extension
    name = Path(filename).stem.lower()
    
    # Try to find episode number (numbers possibly followed by a letter, e.g., 100a)
    # 1. Look for patterns like _NNN or -NNN
    match = re.search(rf"{podcast_source}_(\d+[a-z]?)", name)
    if not match:
        # Generic fallback for any number-like pattern if podcast name isn't prefix
        match = re.search(r"(\d+[a-z]?)", name)
    
    if match:
        episode_num = match.group(1)
        return f"{podcast_source}_{episode_num}"
    
    # Final fallback: use a cleaned version of the filename if no number found
    clean_name = re.sub(r'[^a-z0-0_]', '', name.replace('-', '_'))
    return f"{podcast_source}_{clean_name[:20]}"


def format_path(path: Union[str, Path]) -> str:
    """Return a safe, short representation of `path` for logging.

    - If `path` is inside the current working directory, returns a relative
      path (safer to log).
    - Otherwise returns only the filename to avoid exposing absolute paths.
    """
    try:
        p = Path(path)
    except Exception:
        return str(path)

    try:
        p_res = p.resolve()
    except Exception:
        return str(p)

    try:
        rel = p_res.relative_to(Path.cwd().resolve())
        return str(rel)
    except Exception:
        return p_res.name


__all__ = ["format_path"]
