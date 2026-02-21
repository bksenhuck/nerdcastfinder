"""
Logging utilities
"""
import sys
from typing import Optional


class Logger:
    """Simple logging utility for consistent output"""
    
    @staticmethod
    def info(message: str):
        """Print info message"""
        print(f"ℹ️  {message}")
    
    @staticmethod
    def success(message: str):
        """Print success message"""
        print(f"✓ {message}")
    
    @staticmethod
    def error(message: str):
        """Print error message"""
        print(f"✗ {message}", file=sys.stderr)
    
    @staticmethod
    def warning(message: str):
        """Print warning message"""
        print(f"⚠️  {message}")
    
    @staticmethod
    def header(message: str, width: int = 60):
        """Print a header"""
        print("\n" + "=" * width)
        print(message)
        print("=" * width + "\n")
    
    @staticmethod
    def section(message: str):
        """Print a section header"""
        print(f"\n{message}")
    
    @staticmethod
    def progress(current: int, total: int, item_name: Optional[str] = None):
        """Print progress information"""
        progress_bar = f"[{current}/{total}]"
        if item_name:
            print(f"{progress_bar} {item_name}")
        else:
            print(progress_bar)


# Create a singleton instance
logger = Logger()
