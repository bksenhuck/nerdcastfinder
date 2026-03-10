import sqlite3
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.utils.path_utils import get_stable_id

def migrate():
    db_path = settings.get_database_path()
    logger.header("MIGRAÇÃO DE BANCO DE DADOS: ADD STABLE_ID")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # 1. Adicionar colunas se não existirem
        logger.section("1. Verificando colunas...")
        tables = ['podcast_episodes', 'podcast_segments']
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [info[1] for info in cursor.fetchall()]
            if 'stable_id' not in columns:
                logger.info(f"Adicionando coluna 'stable_id' na tabela {table}...")
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN stable_id TEXT")
                cursor.execute(f"CREATE INDEX idx_{table}_stable_id ON {table}(stable_id)")
        
        # 2. Popular stable_id em podcast_episodes
        logger.section("2. Populando stable_id em podcast_episodes...")
        cursor.execute("SELECT id, filename, podcast_source FROM podcast_episodes WHERE stable_id IS NULL")
        episodes = cursor.fetchall()
        logger.info(f"Processando {len(episodes)} episódios...")
        
        for ep_id, filename, source in episodes:
            sid = get_stable_id(filename, source)
            cursor.execute("UPDATE podcast_episodes SET stable_id = ? WHERE id = ?", (sid, ep_id))
        
        # 3. Popular stable_id em podcast_segments (baseado no campo 'episode')
        logger.section("3. Populando stable_id em podcast_segments...")
        cursor.execute("SELECT id, episode, podcast_source FROM podcast_segments WHERE stable_id IS NULL")
        segments = cursor.fetchall()
        logger.info(f"Processando {len(segments)} segmentos...")
        
        for seg_id, episode_filename, source in segments:
            sid = get_stable_id(episode_filename, source)
            cursor.execute("UPDATE podcast_segments SET stable_id = ? WHERE id = ?", (sid, seg_id))
            
        conn.commit()
        logger.success("Migração concluída com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro na migração: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
