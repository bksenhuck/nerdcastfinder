"""Check embedding dimensions in database"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(Path(__file__).parent))

from app.db.session import get_db_session
from app.db.models import PodcastSegment
from utils.logger import logger

db = get_db_session()

logger.section("Checking embedding dimensions in database")

segments = db.query(PodcastSegment).all()
logger.info(f"Total segments: {len(segments)}")

dimension_counts = {}
none_count = 0

for seg in segments:
    emb = seg.get_embedding()
    if emb is None:
        none_count += 1
    else:
        dim = emb.shape[0]
        dimension_counts[dim] = dimension_counts.get(dim, 0) + 1

logger.info(f"\nEmbedding dimension distribution:")
for dim, count in sorted(dimension_counts.items()):
    logger.info(f"  {dim} dims: {count} segments")

if none_count > 0:
    logger.warning(f"  None: {none_count} segments")

db.close()

# Recommendation
if len(dimension_counts) > 1:
    logger.warning("\n⚠️  MIXED DIMENSIONS DETECTED!")
    logger.info("Database has embeddings from different models.")
    logger.info("Options:")
    logger.info("  1. Delete all segments: python -c \"from backend.app.db.session import get_db_session; from backend.app.db.models import PodcastSegment; db = get_db_session(); db.query(PodcastSegment).delete(); db.commit(); db.close()\"")
    logger.info("  2. Or delete only old dimension segments and keep the new ones")
elif len(dimension_counts) == 1:
    dim = list(dimension_counts.keys())[0]
    logger.success(f"\n✓ All embeddings have same dimension: {dim}")
    logger.info("Safe to rebuild FAISS index")
