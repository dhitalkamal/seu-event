"""MinIO S3-compatible storage client for event cover images."""

from __future__ import annotations

import logging
import uuid
from io import BytesIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)


def _client() -> boto3.client:
    """Build a boto3 S3 client pointed at MinIO."""
    return boto3.client(
        "s3",
        endpoint_url=f"http://{settings.MINIO_ENDPOINT}",
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def _ensure_bucket(client: boto3.client) -> None:
    """Create the bucket if it does not already exist."""
    try:
        client.head_bucket(Bucket=settings.MINIO_BUCKET)
    except ClientError:
        client.create_bucket(Bucket=settings.MINIO_BUCKET)
        client.put_bucket_policy(
            Bucket=settings.MINIO_BUCKET,
            Policy=(
                '{"Version":"2012-10-17","Statement":[{"Effect":"Allow",'
                '"Principal":"*","Action":"s3:GetObject",'
                f'"Resource":"arn:aws:s3:::{settings.MINIO_BUCKET}/*"'
                "}]}"
            ),
        )


def upload_image(file_data: bytes, content_type: str, extension: str) -> str:
    """
    Upload image bytes to MinIO and return the public URL.

    @param file_data - raw bytes of the image
    @param content_type - MIME type e.g. image/jpeg
    @param extension - file extension without dot e.g. jpg
    @returns public URL to the uploaded file
    """
    client = _client()
    _ensure_bucket(client)

    key = f"covers/{uuid.uuid4()}.{extension}"
    client.upload_fileobj(
        BytesIO(file_data),
        settings.MINIO_BUCKET,
        key,
        ExtraArgs={"ContentType": content_type},
    )
    return f"{settings.MINIO_PUBLIC_URL}/{settings.MINIO_BUCKET}/{key}"
