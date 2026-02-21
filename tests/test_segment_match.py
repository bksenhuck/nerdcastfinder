import sqlite3

conn = sqlite3.connect('backend/data/nerdcasts.db')
cursor = conn.cursor()

# Get a segment filename
cursor.execute("SELECT episode FROM nerdcast_segments LIMIT 1")
segment_episode = cursor.fetchone()[0]
print(f"Segment episode: {segment_episode}")

# Check if this episode exists in nerdcast_episodes
cursor.execute("SELECT filename, title_original, published_date, duration_seconds, file_size_mb FROM nerdcast_episodes WHERE filename = ?", (segment_episode,))
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
    
    # Check what filenames exist in nerdcast_episodes
    cursor.execute("SELECT filename FROM nerdcast_episodes LIMIT 5")
    episodes = cursor.fetchall()
    print(f"\nSample filenames in nerdcast_episodes:")
    for ep in episodes:
        print(f"  - {ep[0]}")

conn.close()
