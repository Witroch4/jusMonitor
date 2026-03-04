"""S3-compatible storage client for uploading scraped documents."""

import logging

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger(__name__)

_s3_client = None


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.s3_endpoint}",
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=BotoConfig(
                signature_version="s3v4",
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )
    return _s3_client


def upload_file(key: str, data: bytes, content_type: str = "application/pdf") -> str:
    """Upload file to S3 and return the object key URL (internal reference).

    NOTE: The bucket is private. This URL is stored in the DB and converted to
    a presigned URL on-demand by the backend /api/v1/storage/presign endpoint.

    Args:
        key: S3 object key (e.g. "processos/1234567-89.2025.4.01.3904/docs/01_sentenca.pdf")
        data: File content as bytes.
        content_type: MIME type.

    Returns:
        Path-style URL of the uploaded object (unauthenticated — for DB storage only).
    """
    client = _get_s3_client()
    bucket = settings.s3_bucket

    try:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        url = f"https://{settings.s3_endpoint}/{bucket}/{key}"
        logger.info("s3_upload_ok", extra={"key": key, "size": len(data)})
        return url
    except ClientError as e:
        logger.error("s3_upload_error", extra={"key": key, "error": str(e)})
        raise


def generate_presigned_url(key: str, expiry_seconds: int = 3600) -> str:
    """Generate a presigned GET URL for a private S3 object.

    Args:
        key: S3 object key (e.g. "processos/.../documentos/72982910.pdf").
        expiry_seconds: URL validity window. Default: 1 hour.

    Returns:
        Time-limited presigned URL that can be used directly in a browser.
    """
    client = _get_s3_client()
    bucket = settings.s3_bucket

    try:
        presigned = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiry_seconds,
        )
        logger.info("s3_presign_ok", extra={"key": key, "expiry": expiry_seconds})
        return presigned
    except ClientError as e:
        logger.error("s3_presign_error", extra={"key": key, "error": str(e)})
        raise
