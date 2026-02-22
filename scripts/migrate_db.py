"""
Migration script to add new columns to podcast_episodes table
(Legacy script - consider using backend/pipelines/migrate_to_multi_podcast.py instead)
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(Path(__file__).parent))

from app.config.settings import settings
from utils.logger import logger
import sqlite3

def migrate():
    """Add new columns to existing database"""
    db_path = settings.get_database_path()
    
    logger.section(f"Migrando database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if table has been migrated to new name
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Use new table name if it exists, otherwise use old name
        table_name = 'podcast_episodes' if 'podcast_episodes' in tables else 'nerdcast_episodes'
        
        if table_name == 'nerdcast_episodes':
            logger.warning("⚠️  Usando tabela antiga 'nerdcast_episodes'")
            logger.info("   Considere executar: python -m backend.pipelines.migrate_to_multi_podcast")
        
        # Check existing columns
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [col[1] for col in cursor.fetchall()]
        
        migrations_done = []
        
        # Add downloaded_at column
        if 'downloaded_at' in columns:
            logger.info("✓ Coluna 'downloaded_at' já existe")
        else:
            cursor.execute(f"""
                ALTER TABLE {table_name}
                ADD COLUMN downloaded_at DATETIME
            """)
            migrations_done.append("downloaded_at")
        
        # Add summary column
        if 'summary' in columns:
            logger.info("✓ Coluna 'summary' já existe")
        else:
            cursor.execute(f"""
                ALTER TABLE {table_name}
                ADD COLUMN summary TEXT
            """)
            migrations_done.append("summary")
        
        # Add image_url column
        if 'image_url' in columns:
            logger.info("✓ Coluna 'image_url' já existe")
        else:
            cursor.execute(f"""
                ALTER TABLE {table_name}
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
