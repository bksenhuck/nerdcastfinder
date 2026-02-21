import sqlite3

conn = sqlite3.connect('backend/data/nerdcasts.db')
cursor = conn.cursor()

# Filename que apareceu no resultado da API
episode_name = "empreendedor_67_-_debetti_tradição_e_inovação"

cursor.execute("SELECT filename, title_original, published_date, duration_seconds, file_size_mb FROM podcast_episodes WHERE filename = ?", (episode_name,))
result = cursor.fetchone()

if result:
    print(f"FOUND EXACT MATCH:")
    print(f"Filename: {result[0]}")
    print(f"Title: {result[1]}")
    print(f"Published: {result[2]}")
    print(f"Duration: {result[3]}")
    print(f"Size: {result[4]}")
else:
    print(f"NOT FOUND: {episode_name}")
    
    # Try to find similar names
    cursor.execute("SELECT filename FROM podcast_episodes WHERE filename LIKE 'empreendedor_67%'")
    similar = cursor.fetchall()
    if similar:
        print(f"\nSimilar filenames found:")
        for s in similar:
            print(f"  - {s[0]}")

conn.close()
