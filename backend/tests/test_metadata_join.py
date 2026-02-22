"""
Test if episode metadata is being retrieved correctly
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app.db.session import get_db_session
from backend.app.db.models import PodcastEpisode, PodcastSegment

db = get_db_session()

# Get a segment
segment = db.query(NerdcastSegment).first()
print(f"Segment episode: {segment.episode}")

# Get episode metadata
episode_metadata = db.query(NerdcastEpisode).filter(
    NerdcastEpisode.filename == segment.episode
).first()

if episode_metadata:
    print(f"Title: {episode_metadata.title_original}")
    print(f"Published: {episode_metadata.published_date}")
    print(f"Duration: {episode_metadata.duration_seconds}")
    print(f"Size: {episode_metadata.file_size_mb}")
    print(f"Image URL: {episode_metadata.image_url}")
else:
    print("No metadata found")

db.close()
