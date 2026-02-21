import sqlite3

conn = sqlite3.connect('backend/data/nerdcasts.db')
cursor = conn.cursor()

cursor.execute("SELECT filename, title_original, published_date, duration_seconds, file_size_mb FROM podcast_episodes WHERE filename LIKE 'empreendedor_61%'")
result = cursor.fetchone()

if result:
    print(f'Filename: {result[0]}')
    print(f'Title: {result[1]}')
    print(f'Published: {result[2]}')
    print(f'Duration: {result[3]} seconds')
    print(f'Size: {result[4]} MB')
else:
    print("Not found")

conn.close()
