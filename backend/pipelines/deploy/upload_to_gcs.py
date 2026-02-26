"""
Upload local data artifacts to Google Cloud Storage

This script:
1. Checkpoints the SQLite WAL into the main DB file (ensures consistency)
2. Uploads podcast_database.db, podcasts.index and embedding_id_mapping.npy to GCS
3. Optionally triggers a Cloud Run redeploy

Usage:
    python -m backend.pipelines.deploy.upload_to_gcs
    python -m backend.pipelines.deploy.upload_to_gcs --deploy          # also redeploy Cloud Run
    python -m backend.pipelines.deploy.upload_to_gcs --db-only         # only upload DB
    python -m backend.pipelines.deploy.upload_to_gcs --index-only      # only upload FAISS index + mapping

Requirements:
    - GOOGLE_APPLICATION_CREDENTIALS or gcloud auth already configured
    - pip install google-cloud-storage

GCS URIs are read from env vars (same as Cloud Run):
    FAISS_GCS_URI          e.g. gs://podcast-finder-data/podcasts.index
    FAISS_MAPPING_GCS_URI  e.g. gs://podcast-finder-data/embedding_id_mapping.npy
    FAISS_DB_GCS_URI       e.g. gs://podcast-finder-data/podcast_database.db
"""
import sys
import sqlite3
import argparse
import subprocess
from pathlib import Path

from backend.app.core.config import settings
from backend.app.core.logger import logger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_gcs_uri(uri: str):
    """Return (bucket_name, blob_name) from a gs://bucket/path URI."""
    if not uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI: {uri}")
    _, rest = uri.split("gs://", 1)
    bucket_name, blob_name = rest.split("/", 1)
    return bucket_name, blob_name


def checkpoint_wal(db_path: Path):
    """
    Flush the SQLite WAL into the main database file.

    Must be done before uploading podcast_database.db to GCS, otherwise the uploaded
    file may be missing data that was only written to the WAL journal.
    """
    logger.info(f"[WAL] Checkpointing WAL into {db_path.name}...")
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
        logger.success("[WAL] Checkpoint complete — WAL flushed into main DB file")
    except Exception as e:
        conn.close()
        raise RuntimeError(f"WAL checkpoint failed: {e}") from e


def upload_file(local_path: Path, gcs_uri: str):
    """Upload a single local file to GCS."""
    try:
        from google.cloud import storage as gcs
    except ImportError:
        raise ImportError(
            "google-cloud-storage is not installed. "
            "Run: pip install google-cloud-storage"
        )

    bucket_name, blob_name = _parse_gcs_uri(gcs_uri)
    size_mb = local_path.stat().st_size / (1024 * 1024)

    logger.info(f"[GCS] Uploading {local_path.name} ({size_mb:.1f} MB) → {gcs_uri}")
    client = gcs.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(local_path))
    logger.success(f"[GCS] ✓ {local_path.name} uploaded")


# ---------------------------------------------------------------------------
# Upload steps
# ---------------------------------------------------------------------------

def upload_db():
    db_gcs_uri = settings.get_gcs_db_uri()
    db_path = settings.get_database_path()
    if not db_path.exists():
        logger.error(f"[DB] Database not found at {db_path}")
        return False
    checkpoint_wal(db_path)
    upload_file(db_path, db_gcs_uri)
    return True


def upload_index():
    index_gcs_uri = settings.get_gcs_index_uri()
    mapping_gcs_uri = settings.get_gcs_mapping_uri()

    index_path = settings.get_faiss_index_path()
    mapping_path = settings.get_faiss_dir() / "embedding_id_mapping.npy"

    if not index_path.exists():
        logger.error(f"[INDEX] FAISS index not found at {index_path}")
        return False

    if not mapping_path.exists():
        logger.error(f"[INDEX] Mapping file not found at {mapping_path}")
        return False

    upload_file(index_path, index_gcs_uri)
    upload_file(mapping_path, mapping_gcs_uri)
    return True


def trigger_deploy():
    """Redeploy Cloud Run using the current image (picks up fresh GCS data)."""
    image = settings.get_docker_image()
    cmd = [
        "gcloud", "run", "deploy", settings.CLOUDRUN_SERVICE,
        "--image", image,
        "--region", settings.GCP_REGION,
        "--platform", "managed",
    ]
    logger.info(f"[DEPLOY] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False, shell=True)
    if result.returncode == 0:
        logger.success("[DEPLOY] Cloud Run redeployed successfully")
        return True
    else:
        logger.error(f"[DEPLOY] gcloud run deploy failed (exit {result.returncode})")
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Upload data artifacts to GCS (with WAL checkpoint)"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--db-only",
        action="store_true",
        help="Upload only the SQLite database"
    )
    group.add_argument(
        "--index-only",
        action="store_true",
        help="Upload only the FAISS index and mapping"
    )
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Trigger a Cloud Run redeploy after uploading"
    )
    args = parser.parse_args()

    logger.header("GCS UPLOAD")

    ok = True

    if args.db_only:
        ok = upload_db()
    elif args.index_only:
        ok = upload_index()
    else:
        # Default: upload everything
        db_ok = upload_db()
        idx_ok = upload_index()
        ok = db_ok and idx_ok

    if not ok:
        logger.error("One or more uploads failed — aborting")
        sys.exit(1)

    logger.success("All files uploaded to GCS")

    if args.deploy:
        deploy_ok = trigger_deploy()
        if not deploy_ok:
            sys.exit(1)
    else:
        logger.info(
            "Tip: run with --deploy to also trigger a Cloud Run redeploy, "
            "or run manually:\n"
            f"  gcloud run deploy {settings.CLOUDRUN_SERVICE} "
            f"--image {settings.get_docker_image()} "
            f"--region {settings.GCP_REGION} --platform managed"
        )


if __name__ == "__main__":
    main()
