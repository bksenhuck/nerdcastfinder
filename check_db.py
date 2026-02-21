"""Quick script to check metadata database"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.db.session import get_db_session
from backend.app.db.models import NerdcastEpisode

db = get_db_session()

episodes = db.query(NerdcastEpisode).all()
print(f"\n✓ Total episodes no DB: {len(episodes)}\n")

for ep in episodes:
    print(f"  📝 {ep.filename}")
    print(f"     Título: {ep.title_original}")
    print(f"     Status: {ep.status}")
    print(f"     Data publicação: {ep.published_date}")
    print(f"     Data download: {ep.downloaded_at}")
    print(f"     Duração: {ep.duration_seconds}s")
    print(f"     Tamanho: {ep.file_size_mb:.2f}MB")
    print()

db.close()
