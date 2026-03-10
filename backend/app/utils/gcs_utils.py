"""
Google Cloud Storage utilities — shared between upload_to_gcs and main.py.

Provides:
  - parse_gcs_uri()  split a gs://bucket/path URI into (bucket_name, blob_name)
"""
from typing import Tuple


def parse_gcs_uri(uri: str) -> Tuple[str, str]:
    """
    Split a GCS URI into (bucket_name, blob_name).

    Args:
        uri: A string like "gs://my-bucket/path/to/file"

    Returns:
        Tuple of (bucket_name, blob_name)

    Raises:
        ValueError: if the URI does not start with "gs://"
    """
    if not uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI (must start with gs://): {uri}")
    _, rest = uri.split("gs://", 1)
    bucket_name, blob_name = rest.split("/", 1)
    return bucket_name, blob_name
