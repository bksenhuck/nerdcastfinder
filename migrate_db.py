"""
Migration script to add downloaded_at column to nerdcast_episodes table
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.config.settings import settings
from app.utils.logger import logger
import sqlite3

def migrate():
    """Add downloaded_at column to existing database"""
    db_path = settings.get_database_path()
    
    logger.section(f"Migrando database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(nerdcast_episodes)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'downloaded_at' in columns:
            logger.success("✓ Coluna 'downloaded_at' já existe")
        else:
            # Add the column
            cursor.execute("""
                ALTER TABLE nerdcast_episodes 
                ADD COLUMN downloaded_at DATETIME
            """)
            conn.commit()
            logger.success("✓ Coluna 'downloaded_at' adicionada com sucesso!")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Erro na migração: {e}")
        conn.close()
        raise

if __name__ == "__main__":
    migrate()
