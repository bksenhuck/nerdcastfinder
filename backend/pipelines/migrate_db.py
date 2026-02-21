"""
Migration script to add new columns to nerdcast_episodes table

Usage:
    python -m backend.pipelines.migrate_db
"""
import sqlite3
from pathlib import Path

from backend.app.core.config import settings
from backend.app.core.logger import logger

def migrate():
    """Add new columns to existing database"""
    db_path = settings.get_database_path()
    
    logger.section(f"Migrando database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(nerdcast_episodes)")
        columns = [col[1] for col in cursor.fetchall()]
        
        migrations_done = []
        
        # Add downloaded_at column
        if 'downloaded_at' in columns:
            logger.info("✓ Coluna 'downloaded_at' já existe")
        else:
            cursor.execute("""
                ALTER TABLE nerdcast_episodes 
                ADD COLUMN downloaded_at DATETIME
            """)
            migrations_done.append("downloaded_at")
        
        # Add summary column
        if 'summary' in columns:
            logger.info("✓ Coluna 'summary' já existe")
        else:
            cursor.execute("""
                ALTER TABLE nerdcast_episodes 
                ADD COLUMN summary TEXT
            """)
            migrations_done.append("summary")
        
        # Add image_url column
        if 'image_url' in columns:
            logger.info("✓ Coluna 'image_url' já existe")
        else:
            cursor.execute("""
                ALTER TABLE nerdcast_episodes 
                ADD COLUMN image_url TEXT
            """)
            migrations_done.append("image_url")
        
        if migrations_done:
            conn.commit()
            logger.success(f"✓ Colunas adicionadas: {', '.join(migrations_done)}")
        else:
            logger.success("✓ Todas as colunas já existem, nenhuma migração necessária")
        
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Erro na migração: {e}")
        conn.close()
        raise

if __name__ == "__main__":
    migrate()
