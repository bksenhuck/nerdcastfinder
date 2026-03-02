
import sqlite3
import numpy as np
from pathlib import Path

def debug_ids():
    db_path = 'backend/data/podcast_database.db'
    mapping_path = 'backend/data/faiss_index/embedding_id_mapping.npy'
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    print("--- INFO NO BANCO (podcast_database) ---")
    cur.execute("SELECT podcast_source, MIN(embedding_id), MAX(embedding_id), COUNT(*) FROM podcast_segments GROUP BY podcast_source")
    for row in cur.fetchall():
        print(f"Podcast: {row[0]}, Min ID: {row[1]}, Max ID: {row[2]}, Count: {row[3]}")
    
    print("\n--- INFO NO FAISS MAPPING ---")
    mapping = np.load(mapping_path)
    print(f"Total no mapping: {len(mapping)}")
    print(f"Min no mapping: {np.min(mapping)}")
    print(f"Max no mapping: {np.max(mapping)}")
    
    # Verificar se os últimos IDs do Nerdcast no banco estão no mapping
    cur.execute("SELECT embedding_id FROM podcast_segments WHERE podcast_source='nerdcast' ORDER BY embedding_id DESC LIMIT 5")
    last_nc_ids = [r[0] for r in cur.fetchall()]
    print(f"\nÚltimos 5 IDs do Nerdcast no DB: {last_nc_ids}")
    
    mapping_set = set(mapping)
    present = [id for id in last_nc_ids if id in mapping_set]
    print(f"Desses, quantos estão no FAISS: {len(present)}")
    if present:
        print(f"IDs presentes: {present}")
    
    conn.close()

if __name__ == '__main__':
    debug_ids()
