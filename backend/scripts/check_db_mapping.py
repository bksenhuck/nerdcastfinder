from backend.app.db.session import get_db_session
from backend.app.db.models import PodcastSegment
from backend.app.core.config import settings
import numpy as np

if __name__ == '__main__':
    db = get_db_session()
    try:
        total = db.query(PodcastSegment).count()
        print('DB total segments:', total)
        sample = db.query(PodcastSegment).limit(5).all()
        print('Sample segments:', [(s.episode, s.embedding_id, s.embedding is not None) for s in sample])
        faiss_map_path = settings.get_faiss_dir() / 'embedding_id_mapping.npy'
        print('Mapping exists:', faiss_map_path.exists(), str(faiss_map_path))
        if faiss_map_path.exists():
            arr = np.load(str(faiss_map_path))
            print('Mapping length:', len(arr), 'first 10 ids:', arr[:10])
    finally:
        db.close()
