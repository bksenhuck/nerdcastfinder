"""
Build Docker image with Cloud Build and deploy to Cloud Run

Usage:
    python -m backend.pipelines.deploy.build_and_deploy            # build + deploy
    python -m backend.pipelines.deploy.build_and_deploy --build-only
    python -m backend.pipelines.deploy.build_and_deploy --deploy-only

All infrastructure values are read from environment variables (see .env.example).
"""
import sys
import subprocess
import argparse

from backend.app.core.config import settings
from backend.app.core.logger import logger


def _get_image() -> str:
    return settings.get_docker_image()


def _get_deploy_cmd() -> list:
    image = _get_image()
    env_vars = (
        f"FAISS_GCS_URI={settings.get_gcs_index_uri()},"
        f"FAISS_MAPPING_GCS_URI={settings.get_gcs_mapping_uri()},"
        f"FAISS_DB_GCS_URI={settings.get_gcs_db_uri()},"
        "HF_HUB_OFFLINE=1"  # Use baked model cache, no HuggingFace API calls at runtime
    )
    return [
        "gcloud", "run", "deploy", settings.CLOUDRUN_SERVICE,
        "--image", image,
        "--region", settings.GCP_REGION,
        "--platform", "managed",
        "--allow-unauthenticated",
        "--set-env-vars", env_vars,
        "--memory=2Gi",
        "--cpu=1",
        "--concurrency=1",
        "--timeout=1000s",
    ]


def build():
    image = _get_image()
    cmd = ["gcloud", "builds", "submit", "--tag", image]
    logger.info(f"[BUILD] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        logger.error(f"[BUILD] gcloud builds submit failed (exit {result.returncode})")
        return False
    logger.success("[BUILD] Image built and pushed successfully")
    return True


def deploy():
    cmd = _get_deploy_cmd()
    logger.info(f"[DEPLOY] Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        logger.error(f"[DEPLOY] gcloud run deploy failed (exit {result.returncode})")
        return False
    logger.success("[DEPLOY] Cloud Run deployed successfully")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Build Docker image and/or deploy to Cloud Run"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--build-only", action="store_true", help="Only build the image")
    group.add_argument(
        "--deploy-only", action="store_true", help="Only redeploy using existing image"
    )
    args = parser.parse_args()

    if args.build_only:
        ok = build()
    elif args.deploy_only:
        ok = deploy()
    else:
        logger.header("BUILD + DEPLOY")
        ok = build() and deploy()

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
