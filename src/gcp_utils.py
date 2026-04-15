"""
SkyPipe — Google Cloud utilities: GCS, signed URLs, upload validation.

Google client libraries are imported lazily so local Spark/CLI usage works without
installing google-cloud-* (e.g. interrupted pip, or spark-only workflows).
"""

from __future__ import annotations

import logging
import mimetypes
import os
import re
import uuid
from datetime import timedelta
from typing import Any

logger = logging.getLogger("skypipe.gcp")

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json", ".parquet", ".pq"}
MAX_UPLOAD_BYTES_DEFAULT = 500 * 1024 * 1024


def get_gcs_client():
    from google.cloud import storage

    return storage.Client()


def load_credentials_from_env():
    from google.oauth2 import service_account

    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if path and os.path.isfile(path):
        return service_account.Credentials.from_service_account_file(path)
    return None


def detect_format_from_filename(filename: str) -> str:
    base = filename.lower().strip()
    ext = os.path.splitext(base)[1]
    if ext in (".pq",):
        return "parquet"
    if ext in (".xlsx", ".xls"):
        return "excel"
    if ext == ".csv":
        return "csv"
    if ext == ".json":
        return "json"
    return "unknown"


def validate_upload_filename(filename: str) -> tuple[bool, str]:
    if not filename or ".." in filename or filename.startswith("/"):
        return False, "Invalid filename."
    safe = re.sub(r"[^a-zA-Z0-9._\-]", "_", os.path.basename(filename))
    ext = os.path.splitext(safe)[1].lower()
    if ext not in ALLOWED_EXTENSIONS and ext != "":
        return False, f"Extension not allowed. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
    if ext == "":
        return False, "File must have an extension."
    return True, safe


def read_upload_head(data: bytes, n: int = 4096) -> bytes:
    return data[:n]


def sniff_format_from_bytes(filename: str, head: bytes) -> str:
    """Automatic format detection: filename first, then magic bytes."""
    by_name = detect_format_from_filename(filename)
    if by_name != "unknown":
        return by_name
    if len(head) >= 4 and head[:4] == b"PAR1":
        return "parquet"
    if head.strip().startswith(b"{") or head.strip().startswith(b"["):
        return "json"
    return "csv"


def upload_bytes_to_gcs(
    bucket_name: str,
    object_name: str,
    data: bytes,
    content_type: str | None = None,
    metadata: dict[str, str] | None = None,
) -> str:
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    ct = content_type or mimetypes.guess_type(object_name)[0] or "application/octet-stream"
    blob.content_type = ct
    if metadata:
        blob.metadata = metadata
    blob.upload_from_string(data, content_type=ct)
    gs_uri = f"gs://{bucket_name}/{object_name}"
    logger.info("Uploaded to %s", gs_uri)
    return gs_uri


def generate_signed_url_read(
    bucket_name: str,
    object_name: str,
    expiration_minutes: int = 60,
) -> str:
    client = get_gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    url = blob.generate_signed_url(
        version="v4",
        expiration=timedelta(minutes=expiration_minutes),
        method="GET",
    )
    return url


def new_job_id() -> str:
    return str(uuid.uuid4())
