"""
Cloudflare R2 helpers (S3-compatible).
Used to generate signed URLs for video output delivery.
"""
import logging

import boto3
from botocore.client import Config

from app.config import Settings

logger = logging.getLogger(__name__)


def _client(settings: Settings):
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def generate_signed_url(key: str, settings: Settings) -> str:
    """Generate a pre-signed GET URL for an existing R2 object."""
    client = _client(settings)
    url = client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.r2_bucket, "Key": key},
        ExpiresIn=settings.r2_signed_url_expiry,
    )
    logger.info("signed URL generated for key=%s", key)
    return url


def upload_bytes(data: bytes, key: str, content_type: str, settings: Settings) -> str:
    """Upload raw bytes to R2 and return a signed URL."""
    client = _client(settings)
    client.put_object(
        Bucket=settings.r2_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    logger.info("uploaded %d bytes to R2 key=%s", len(data), key)
    return generate_signed_url(key, settings)
