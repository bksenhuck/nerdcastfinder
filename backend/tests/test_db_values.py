import sqlite3
import json

conn = sqlite3.connect('backend/data/nerdcasts.db')
cursor = conn.cursor()

episode_name = "empreendedor_67_-_debetti_tradição_e_inovação"

cursor.execute("""
    SELECT 
        filename, 
        title_original, 
        published_date, 
        duration_seconds, 
        file_size_mb,
        image_url
    FROM podcast_episodes 
    WHERE filename = ?
""", (episode_name,))

result = cursor.fetchone()

if result:
    print("Database values:")
    print(f"  filename: {result[0]}")
    print(f"  title_original: {result[1]}")
    print(f"  published_date: {result[2]} (type: {type(result[2])})")
    print(f"  duration_seconds: {result[3]} (type: {type(result[3])})")
    print(f"  file_size_mb: {result[4]} (type: {type(result[4])})")
    print(f"  image_url: {result[5][:50] if result[5] else None}...")
    
    # Simulate what the API should return
    api_response = {
        "episode": result[0],
        "title": result[1],
        "published_date": result[2],
        "duration_seconds": result[3],
        "file_size_mb": result[4],
        "image_url": result[5]
    }
    
    print("\nSimulated API response:")
    print(json.dumps(api_response, indent=2))

conn.close()
