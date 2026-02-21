"""
Database session management
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.app.core.config import settings
from backend.app.db.models import Base

# Get database URL from settings
DATABASE_URL = settings.get_database_url()

# Create engine with optimized SQLite settings for concurrent writes
if "sqlite" in DATABASE_URL:
    # Use StaticPool to avoid threading issues with SQLite
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 30  # 30 second timeout for database locks
        },
        echo=settings.DB_ECHO,
        poolclass=StaticPool
    )
    
    # Enable WAL mode for better concurrent write performance
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Enable WAL mode and optimize SQLite for concurrent writes"""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
        cursor.execute("PRAGMA synchronous=NORMAL")  # Faster writes
        cursor.execute("PRAGMA cache_size=10000")  # Larger cache
        cursor.execute("PRAGMA busy_timeout=30000")  # 30s timeout
        cursor.close()
else:
    # For other databases (PostgreSQL, etc)
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": settings.DB_CHECK_SAME_THREAD},
        echo=settings.DB_ECHO
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """Get database session (for scripts)"""
    return SessionLocal()
