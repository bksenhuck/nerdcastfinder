"""
Update all episode metadata from RSS feed
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.scripts.download_podcasts import fetch_feed, extract_episode_info, save_all_episode_metadata, normalize_filename

if __name__ == "__main__":
    print("Fetching RSS feed...")
    feed = fetch_feed('https://jovemnerd.com.br/feed-nerdcast/')
    
    if not feed:
        print("Error fetching feed")
        sys.exit(1)
    
    print(f"Found {len(feed.entries)} episodes in feed")
    print("\nExtracting metadata...")
    
    metadata_list = []
    for entry in feed.entries:
        episode_info = extract_episode_info(entry)
        if episode_info:
            # Add normalized filename and rename 'title' to 'title_original'
            episode_info['filename'] = normalize_filename(episode_info['title'])
            episode_info['title_original'] = episode_info.pop('title')  # Rename key
            # Convert enclosure_length (bytes) to MB
            if episode_info.get('enclosure_length'):
                episode_info['file_size_mb'] = episode_info['enclosure_length'] / (1024 * 1024)
            else:
                episode_info['file_size_mb'] = 0.0
            metadata_list.append(episode_info)
    
    print(f"Extracted metadata for {len(metadata_list)} episodes")
    print("\nSaving to database in batches...")
    
    saved, errors = save_all_episode_metadata(metadata_list)
    
    print(f"\n{'='*60}")
    print(f"✅ Saved: {saved}")
    print(f"❌ Errors: {errors}")
    print(f"{'='*60}")
    print("\nDone!")
