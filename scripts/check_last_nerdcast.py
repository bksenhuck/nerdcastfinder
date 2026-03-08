import sqlite3
import os

db_path = os.path.join('backend', 'data', 'podcast_database.db')
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("--- Últimos NerdCasts (Programa Principal) ---")
cur.execute("""
    SELECT title_original, published_date, status 
    FROM podcast_episodes 
    WHERE title_original LIKE 'NerdCast %' 
    ORDER BY published_date DESC 
    LIMIT 10
""")
for row in cur.fetchall():
    print(f"{row['published_date']} - {row['title_original']} [{row['status']}]")

print("\n--- Últimos NerdCasts Processados (com transcrição) ---")
cur.execute("""
    SELECT DISTINCT episode 
    FROM podcast_segments 
    WHERE episode LIKE 'nerdcast_%'
    ORDER BY episode DESC 
    LIMIT 10
""")
for row in cur.fetchall():
    # Tenta encontrar o título no banco de episódios
    ep_id = row['episode']
    cur.execute("SELECT title_original FROM podcast_episodes WHERE filename = ?", (ep_id,))
    title_row = cur.fetchone()
    title = title_row['title_original'] if title_row else "Título não encontrado"
    print(f"{ep_id} - {title}")

conn.close()
