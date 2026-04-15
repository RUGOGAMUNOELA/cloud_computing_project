"""
Input stage: store raw uploads in a distributed-style object store.
- Production pattern: Amazon S3 or GCS.
- Free local exam pattern: MinIO (S3-compatible) via boto3.
- Fallback: POSIX directory under skypipe/data/uploads (labeled clearly for demos).
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("skypipe.storage")


def upload_input_bytes(
    job_id: str,
    safe_filename: str,
    data: bytes,
    *,
    s3_endpoint: str | None,
    s3_access_key: str | None,
    s3_secret_key: str | None,
    s3_bucket: str | None,
    s3_use_ssl: bool,
    gcs_bucket: str | None,
    gcp_project: str | None,
    local_data_root: str,
) -> tuple[str | None, str, str]:
    """
    Returns (object_uri, stage_label, stage_detail).
    object_uri: gs://, s3://, or None if local-only path returned via separate file path.
    """
    key = f"uploads/{job_id}/{safe_filename}"

    if gcp_project and gcs_bucket:
        from gcp_utils import upload_bytes_to_gcs

        uri = upload_bytes_to_gcs(gcs_bucket, key, data, metadata={"job_id": job_id})
        return uri, "Google Cloud Storage (object store)", f"Object stored at {uri}. This fulfills the shared object storage role for distributed processing."

    if s3_endpoint and s3_access_key and s3_secret_key and s3_bucket:
        import boto3
        from botocore.client import Config

        client = boto3.client(
            "s3",
            endpoint_url=s3_endpoint.rstrip("/"),
            aws_access_key_id=s3_access_key,
            aws_secret_access_key=s3_secret_key,
            config=Config(signature_version="s3v4"),
            region_name="us-east-1",
            use_ssl=s3_use_ssl,
        )
        try:
            client.head_bucket(Bucket=s3_bucket)
        except Exception:
            client.create_bucket(Bucket=s3_bucket)
        client.put_object(Bucket=s3_bucket, Key=key, Body=data, Metadata={"job_id": job_id})
        uri = f"s3://{s3_bucket}/{key}"
        return (
            uri,
            "S3-compatible object storage (MinIO)",
            f"Stored at {uri}. MinIO provides distributed object storage so Spark workers can read the same dataset in parallel.",
        )

    # Local POSIX fallback with clear staging label before Spark
    upload_dir = os.path.join(local_data_root, "uploads", job_id)
    os.makedirs(upload_dir, exist_ok=True)
    path = os.path.join(upload_dir, safe_filename)
    with open(path, "wb") as f:
        f.write(data)
    return (
        None,
        "Local attached storage (development)",
        f"File saved to {path}. In production this would be S3, GCS, or HDFS for multi-node Spark workers.",
    )


def describe_input_uri(object_uri: str | None, local_path: str) -> str:
    if object_uri:
        return object_uri
    return f"file://{local_path}"
