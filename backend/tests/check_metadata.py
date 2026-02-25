"""
Check if metadata is populated in the database
"""
import sqlite3

db_path = "backend/data/podcast_database.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get first 3 episodes
cursor.execute("SELECT filename, title_original, published_date, duration_seconds, file_size_mb, image_url FROM podcast_episodes LIMIT 3")
episodes = cursor.fetchall()

for ep in episodes:
    print(f"\n{'='*60}")
    print(f"Episode: {ep[0]}")
    print(f"Title: {ep[1]}")
    print(f"Published: {ep[2]}")
    print(f"Duration: {ep[3]} seconds")
    print(f"Size: {ep[4]} MB")
    print(f"Image URL: {ep[5][:50] if ep[5] else None}...")

conn.close()
