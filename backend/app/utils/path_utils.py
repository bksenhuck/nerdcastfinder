"""
Path utilities for safe logging and display.

This module centralizes path formatting so callers can log
relative or filename-only values without exposing absolute
filesystem paths.
"""
from pathlib import Path
from typing import Union


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
