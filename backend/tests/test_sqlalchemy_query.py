"""
Test SQLAlchemy query for episode metadata
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.db.session import get_db_session
from backend.app.db.models import PodcastEpisode

db = get_db_session()

# Query the episode
episode_metadata = db.query(PodcastEpisode).filter(
    PodcastEpisode.filename == "empreendedor_67_-_debetti_tradição_e_inovação"
).first()

if episode_metadata:
    print("Episode found via SQLAlchemy!")
    print(f"Title: {episode_metadata.title_original}")
    print(f"Published date: {episode_metadata.published_date}")
    print(f"Published date type: {type(episode_metadata.published_date)}")
    print(f"Duration: {episode_metadata.duration_seconds}")
    print(f"Duration type: {type(episode_metadata.duration_seconds)}")
    print(f"Size: {episode_metadata.file_size_mb}")
    print(f"Size type: {type(episode_metadata.file_size_mb)}")
    
    # Test isoformat conversion
    if episode_metadata.published_date:
        print(f"\nISO format: {episode_metadata.published_date.isoformat()}")
    else:
        print(f"\nPublished date is None/null")
else:
    print("Episode NOT found")

db.close()
