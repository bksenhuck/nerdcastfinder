import sqlite3

conn = sqlite3.connect('backend/data/podcast_database.db')
cursor = conn.cursor()

# Check if table has been migrated to new name
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]

episodes_table = 'podcast_episodes' if 'podcast_episodes' in tables else 'nerdcast_episodes'
segments_table = 'podcast_segments' if 'podcast_segments' in tables else 'nerdcast_segments'

print(f"Using tables: {episodes_table}, {segments_table}")

# Get a segment filename
cursor.execute(f"SELECT episode FROM {segments_table} LIMIT 1")
segment_episode = cursor.fetchone()[0]
print(f"Segment episode: {segment_episode}")

# Check if this episode exists in episodes table
cursor.execute(f"SELECT filename, title_original, published_date, duration_seconds, file_size_mb FROM {episodes_table} WHERE filename = ?", (segment_episode,))
result = cursor.fetchone()

if result:
    print(f"\nFound metadata:")
    print(f"Filename: {result[0]}")
    print(f"Title: {result[1]}")
    print(f"Published: {result[2]}")
    print(f"Duration: {result[3]}")
    print(f"Size: {result[4]}")
else:
    print(f"\nNo metadata found for {segment_episode}")
    
    # Check what filenames exist in episodes table
    cursor.execute(f"SELECT filename FROM {episodes_table} LIMIT 5")
    episodes = cursor.fetchall()
    print(f"\nSample filenames in {episodes_table}:")
    for ep in episodes:
        print(f"  - {ep[0]}")

conn.close()
