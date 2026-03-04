"""S3-compatible storage client for the backend (MinIO / AWS S3).

Provides generate_presigned_url() to create time-limited, signed download
URLs for objects stored in a private bucket.
"""

import logging
from functools import lru_cache

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_s3_client():
    """Return a cached S3 client configured for MinIO."""
    from app.config import settings

    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.s3_endpoint}",
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        config=BotoConfig(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


def _key_from_url(s3_url: str, bucket: str, endpoint: str) -> str | None:
    """Extract the S3 object key from a full S3 URL.

    Handles:
      - https://endpoint/bucket/key
      - https://bucket.endpoint/key  (virtual-hosted style)
    """
    # Path-style: https://endpoint/bucket/key
    prefix_path = f"https://{endpoint}/{bucket}/"
    if s3_url.startswith(prefix_path):
        return s3_url[len(prefix_path):]

    # Virtual-hosted style: https://bucket.endpoint/key
    prefix_virtual = f"https://{bucket}.{endpoint}/"
    if s3_url.startswith(prefix_virtual):
        return s3_url[len(prefix_virtual):]

    return None


def generate_presigned_url(
    s3_url: str,
    expiry_seconds: int | None = None,
) -> str:
    """Generate a presigned GET URL for a private S3 object.

    Args:
        s3_url: The raw S3 URL stored in the database (public-style URL).
        expiry_seconds: TTL for the signed URL. Defaults to settings value.

    Returns:
        A time-limited presigned URL the browser can use directly.

    Raises:
        ValueError: If the URL cannot be mapped to a known bucket/key.
        ClientError: If boto3 fails to generate the presigned URL.
    """
    from app.config import settings

    expiry = expiry_seconds if expiry_seconds is not None else settings.s3_presign_expiry_seconds
    key = _key_from_url(s3_url, settings.s3_bucket, settings.s3_endpoint)

    if key is None:
        raise ValueError(
            f"Cannot extract S3 key from URL: {s3_url!r}. "
            f"Expected prefix https://{settings.s3_endpoint}/{settings.s3_bucket}/"
        )

    try:
        client = _get_s3_client()
        presigned = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.s3_bucket, "Key": key},
            ExpiresIn=expiry,
        )
        logger.debug("presigned_url_generated key=%s expiry=%d", key, expiry)
        return presigned
    except ClientError as exc:
        logger.error("presigned_url_error key=%s error=%s", key, exc)
        raise
