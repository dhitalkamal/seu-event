"""MinIO S3-compatible storage client for event cover images and thumbnails."""

from __future__ import annotations

import logging
import uuid
from io import BytesIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from django.conf import settings

logger = logging.getLogger(__name__)

# thumbnail sizes: (width, height) in pixels
_THUMBNAIL_SIZES: list[tuple[int, int]] = [(200, 200), (400, 400), (800, 800)]


def _client() -> boto3.client:
    """Build a boto3 S3 client pointed at MinIO or any S3-compatible service."""
    endpoint = settings.MINIO_ENDPOINT
    # support full URLs (https://...) or bare host:port for local MinIO
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        endpoint_url = endpoint
    else:
        endpoint_url = f"http://{endpoint}"
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
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


def generate_thumbnails(file_data: bytes) -> list[tuple[tuple[int, int], bytes]]:
    """
    Generate 3 WebP thumbnails from raw image bytes.

    Produces 200x200, 400x400, and 800x800 thumbnails using Pillow.
    Preserves aspect ratio via thumbnail (images may be smaller than target
    if the source is smaller in one dimension).

    @param file_data - raw bytes of any Pillow-supported image format
    @returns list of ((width, height), webp_bytes) for each size
    """
    from PIL import Image

    source = Image.open(BytesIO(file_data))
    # convert to RGB to strip alpha channel before WebP encode
    if source.mode not in ("RGB", "L"):
        source = source.convert("RGB")

    results: list[tuple[tuple[int, int], bytes]] = []
    for size in _THUMBNAIL_SIZES:
        img = source.copy()
        img.thumbnail(size, Image.LANCZOS)
        buf = BytesIO()
        img.save(buf, format="WEBP", quality=85)
        results.append((size, buf.getvalue()))

    return results


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


def upload_image_with_thumbnails(
    file_data: bytes,
    content_type: str,
    extension: str,
) -> dict[str, object]:
    """
    Upload original image plus 3 WebP thumbnails to MinIO.

    Generates thumbnails at 200x200, 400x400, and 800x800, converts all to
    WebP, then uploads each under a suffixed key derived from the original key.

    @param file_data - raw bytes of the source image
    @param content_type - MIME type e.g. image/jpeg
    @param extension - file extension without dot e.g. jpg
    @returns dict with 'url' (original) and 'thumbnail_urls' ({"{w}x{h}": url, ...})
    """
    client = _client()
    _ensure_bucket(client)

    # upload original
    base_key = f"covers/{uuid.uuid4()}.{extension}"
    client.upload_fileobj(
        BytesIO(file_data),
        settings.MINIO_BUCKET,
        base_key,
        ExtraArgs={"ContentType": content_type},
    )
    original_url = f"{settings.MINIO_PUBLIC_URL}/{settings.MINIO_BUCKET}/{base_key}"

    # strip extension from key to build thumbnail key prefix
    key_without_ext = base_key.rsplit(".", 1)[0]

    thumbnail_urls: dict[str, str] = {}
    for size, thumb_bytes in generate_thumbnails(file_data):
        w, h = size
        thumb_key = f"{key_without_ext}_{w}x{h}.webp"
        client.upload_fileobj(
            BytesIO(thumb_bytes),
            settings.MINIO_BUCKET,
            thumb_key,
            ExtraArgs={"ContentType": "image/webp"},
        )
        thumb_url = f"{settings.MINIO_PUBLIC_URL}/{settings.MINIO_BUCKET}/{thumb_key}"
        thumbnail_urls[f"{w}x{h}"] = thumb_url

    return {"url": original_url, "thumbnail_urls": thumbnail_urls}
