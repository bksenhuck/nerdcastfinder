from datetime import datetime
from typing import Optional


class Logger:
    RESET = "\033[0m"

    COLORS = {
        "INFO": "\033[94m",      # Azul
        "SUCCESS": "\033[92m",   # Verde
        "WARNING": "\033[93m",   # Amarelo
        "ERROR": "\033[91m",     # Vermelho
        "HEADER": "\033[95m",    # Magenta
        "SECTION": "\033[96m",   # Ciano
    }

    @staticmethod
    def _timestamp():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def _log(cls, level: str, message: str):
        color = cls.COLORS.get(level, cls.RESET)
        timestamp = cls._timestamp()
        print(f"{color}[{timestamp}] [{level}] {message}{cls.RESET}")

    @classmethod
    def info(cls, message: str):
        cls._log("INFO", message)

    @classmethod
    def success(cls, message: str):
        cls._log("SUCCESS", message)

    @classmethod
    def warning(cls, message: str):
        cls._log("WARNING", message)

    @classmethod
    def error(cls, message: str):
        cls._log("ERROR", message)

    @classmethod
    def header(cls, message: str, width: int = 60):
        """Print a header with borders"""
        color = cls.COLORS.get("HEADER", cls.RESET)
        timestamp = cls._timestamp()
        border = "=" * width
        print(f"\n{color}[{timestamp}] [HEADER]{cls.RESET}")
        print(f"{color}{border}{cls.RESET}")
        print(f"{color}{message}{cls.RESET}")
        print(f"{color}{border}{cls.RESET}\n")

    @classmethod
    def section(cls, message: str):
        """Print a section header"""
        color = cls.COLORS.get("SECTION", cls.RESET)
        timestamp = cls._timestamp()
        print(f"\n{color}[{timestamp}] [SECTION] {message}{cls.RESET}")

    @classmethod
    def progress(cls, current: int, total: int, item_name: Optional[str] = None):
        """Print progress information"""
        color = cls.COLORS.get("INFO", cls.RESET)
        timestamp = cls._timestamp()
        progress_bar = f"[{current}/{total}]"
        if item_name:
            print(f"{color}[{timestamp}] [PROGRESS] {progress_bar} {item_name}{cls.RESET}")
        else:
            print(f"{color}[{timestamp}] [PROGRESS] {progress_bar}{cls.RESET}")


# Create a singleton instance
logger = Logger()
