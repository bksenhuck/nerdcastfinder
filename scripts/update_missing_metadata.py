"""
Script to update missing summary and image_url for existing episodes
"""
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(Path(__file__).parent))

from app.config.settings import settings
from utils.logger import logger
import feedparser

def update_metadata():
    """Update missing metadata from RSS feed"""
    import sqlite3
    
    db_path = settings.get_database_path()
    logger.section("Atualizando metadados faltantes do RSS feed")
    
    # Fetch RSS feed
    logger.info("Buscando RSS feed...")
    feed = feedparser.parse('https://jovemnerd.com.br/feed-nerdcast/')
    
    if not feed.entries:
        logger.error("❌ Erro ao buscar feed")
        return
    
    logger.success(f"✓ {len(feed.entries)} episódios no feed")
    
    # Build lookup dict by title
    feed_data = {}
    for entry in feed.entries:
        title = entry.get('title', '').strip()
        summary = entry.get('summary', '').strip()
        image_url = None
        if 'image' in entry and isinstance(entry['image'], dict):
            image_url = entry['image'].get('href', '')
        
        feed_data[title] = {
            'summary': summary,
            'image_url': image_url
        }
    
    logger.info(f"✓ {len(feed_data)} episódios processados do feed")
    
    # Update database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get episodes without summary or image_url
    cursor.execute("""
        SELECT id, title_original 
        FROM nerdcast_episodes 
        WHERE summary IS NULL OR image_url IS NULL
    """)
    
    episodes_to_update = cursor.fetchall()
    logger.info(f"📝 {len(episodes_to_update)} episódios precisam de atualização")
    
    updated = 0
    not_found = 0
    
    for ep_id, title in episodes_to_update:
        if title in feed_data:
            data = feed_data[title]
            cursor.execute("""
                UPDATE nerdcast_episodes 
                SET summary = ?, image_url = ?
                WHERE id = ?
            """, (data['summary'], data['image_url'], ep_id))
            updated += 1
        else:
            not_found += 1
    
    conn.commit()
    conn.close()
    
    logger.success(f"✓ {updated} episódios atualizados")
    if not_found > 0:
        logger.warning(f"⚠️  {not_found} episódios não encontrados no feed (muito antigos)")

if __name__ == "__main__":
    update_metadata()
