"""Unit tests for thumbnail generation and image upload limit enforcement."""

from __future__ import annotations

import io
import uuid
from unittest.mock import MagicMock, patch

import pytest

from apps.events.infrastructure.storage import generate_thumbnails, upload_image_with_thumbnails


def _make_jpeg_bytes() -> bytes:
    """Build a minimal valid JPEG in memory using Pillow."""
    from PIL import Image

    buf = io.BytesIO()
    img = Image.new("RGB", (1000, 1000), color=(255, 0, 0))
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_png_bytes() -> bytes:
    """Build a minimal valid PNG in memory using Pillow."""
    from PIL import Image

    buf = io.BytesIO()
    img = Image.new("RGB", (600, 400), color=(0, 128, 0))
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture()
def jpeg_bytes() -> bytes:
    """Return raw JPEG image bytes for use in tests."""
    return _make_jpeg_bytes()


@pytest.fixture()
def png_bytes() -> bytes:
    """Return raw PNG image bytes for use in tests."""
    return _make_png_bytes()


class TestGenerateThumbnails:
    """generate_thumbnails produces correctly sized WebP thumbnails."""

    def test_returns_three_thumbnails(self, jpeg_bytes: bytes) -> None:
        """Should produce exactly 3 thumbnails from any input image."""
        thumbnails = generate_thumbnails(jpeg_bytes)
        assert len(thumbnails) == 3

    def test_thumbnail_sizes_are_correct(self, jpeg_bytes: bytes) -> None:
        """Thumbnail sizes must match the required 200x200, 400x400, 800x800 spec."""

        thumbnails = generate_thumbnails(jpeg_bytes)
        sizes = {size for size, _ in thumbnails}
        assert sizes == {(200, 200), (400, 400), (800, 800)}

    def test_thumbnails_are_webp_format(self, jpeg_bytes: bytes) -> None:
        """All generated thumbnails must be in WebP format."""
        from PIL import Image

        thumbnails = generate_thumbnails(jpeg_bytes)
        for _size, data in thumbnails:
            img = Image.open(io.BytesIO(data))
            assert img.format == "WEBP"

    def test_thumbnail_key_suffix_format(self, jpeg_bytes: bytes) -> None:
        """Key suffix for each thumbnail must follow the {width}x{height}.webp pattern."""
        thumbnails = generate_thumbnails(jpeg_bytes)
        suffixes = {f"{w}x{h}.webp" for (w, h), _ in thumbnails}
        assert "200x200.webp" in suffixes
        assert "400x400.webp" in suffixes
        assert "800x800.webp" in suffixes

    def test_png_source_also_produces_webp_thumbnails(self, png_bytes: bytes) -> None:
        """PNG source images must also produce WebP thumbnails."""
        from PIL import Image

        thumbnails = generate_thumbnails(png_bytes)
        assert len(thumbnails) == 3
        for _size, data in thumbnails:
            img = Image.open(io.BytesIO(data))
            assert img.format == "WEBP"

    def test_thumbnail_dimensions_do_not_exceed_target(self, jpeg_bytes: bytes) -> None:
        """Thumbnails must fit within their target bounding box (thumbnail, not exact crop)."""
        from PIL import Image

        thumbnails = generate_thumbnails(jpeg_bytes)
        for (target_w, target_h), data in thumbnails:
            img = Image.open(io.BytesIO(data))
            assert img.width <= target_w
            assert img.height <= target_h


class TestUploadImageWithThumbnails:
    """upload_image_with_thumbnails uploads original + 3 thumbnails and returns URLs."""

    def test_uploads_original_and_three_thumbnails(self, jpeg_bytes: bytes) -> None:
        """Should call upload_fileobj exactly 4 times (1 original + 3 thumbnails)."""
        with patch("apps.events.infrastructure.storage._client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.head_bucket.return_value = {}

            result = upload_image_with_thumbnails(
                file_data=jpeg_bytes,
                content_type="image/jpeg",
                extension="jpg",
            )

        assert mock_client.upload_fileobj.call_count == 4
        assert "url" in result
        assert "thumbnail_urls" in result
        assert len(result["thumbnail_urls"]) == 3

    def test_thumbnail_keys_have_correct_suffixes(self, jpeg_bytes: bytes) -> None:
        """Thumbnail object keys must end with _{width}x{height}.webp."""
        uploaded_keys: list[str] = []

        def capture_upload(buf: object, bucket: str, key: str, **kwargs: object) -> None:
            uploaded_keys.append(key)

        with patch("apps.events.infrastructure.storage._client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.head_bucket.return_value = {}
            mock_client.upload_fileobj.side_effect = capture_upload

            upload_image_with_thumbnails(
                file_data=jpeg_bytes,
                content_type="image/jpeg",
                extension="jpg",
            )

        thumb_keys = uploaded_keys[1:]  # first key is the original
        assert any(k.endswith("_200x200.webp") for k in thumb_keys)
        assert any(k.endswith("_400x400.webp") for k in thumb_keys)
        assert any(k.endswith("_800x800.webp") for k in thumb_keys)

    def test_returned_thumbnail_urls_match_bucket_config(self, jpeg_bytes: bytes) -> None:
        """Thumbnail URLs must be formed from MINIO_PUBLIC_URL and MINIO_BUCKET."""
        with patch("apps.events.infrastructure.storage._client") as mock_client_factory:
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client
            mock_client.head_bucket.return_value = {}

            result = upload_image_with_thumbnails(
                file_data=jpeg_bytes,
                content_type="image/jpeg",
                extension="jpg",
            )

        from django.conf import settings

        for thumb_url in result["thumbnail_urls"].values():
            assert thumb_url.startswith(settings.MINIO_PUBLIC_URL)
            assert settings.MINIO_BUCKET in thumb_url


class TestMediaUploadLimit:
    """EventMediaListCreateView enforces a maximum of 20 images per event."""

    def test_adding_media_beyond_limit_returns_400(self) -> None:
        """POST to event media when 20 images exist must return 400."""
        from unittest.mock import MagicMock, patch

        from rest_framework.test import APIRequestFactory

        from apps.events.infrastructure.models import EventMedia
        from apps.events.presentation.views import EventMediaListCreateView

        factory = APIRequestFactory()
        event_id = uuid.uuid4()

        request = factory.post(
            f"/events/{event_id}/media/",
            data={"url": "http://example.com/img.jpg", "media_type": "image"},
            format="json",
        )
        # force authentication by bypassing DRF auth entirely
        request.user = MagicMock()
        request.user.is_authenticated = True
        request.user.id = uuid.uuid4()
        request.auth = MagicMock()

        with (
            patch("rest_framework.views.APIView.perform_authentication"),
            patch("rest_framework.views.APIView.check_permissions"),
            patch.object(EventMedia.objects, "filter") as mock_filter,
        ):
            mock_qs = MagicMock()
            mock_qs.count.return_value = 20
            mock_filter.return_value = mock_qs

            view = EventMediaListCreateView.as_view()
            response = view(request, event_id=event_id)

        assert response.status_code == 400

    def test_adding_media_within_limit_proceeds_normally(self) -> None:
        """POST to event media when fewer than 20 images exist must not return 400 for the limit."""
        import datetime
        from unittest.mock import MagicMock, patch

        from rest_framework.test import APIRequestFactory

        from apps.events.infrastructure.models import EventMedia
        from apps.events.presentation.views import EventMediaListCreateView

        factory = APIRequestFactory()
        event_id = uuid.uuid4()

        request = factory.post(
            f"/events/{event_id}/media/",
            data={"url": "http://example.com/img.jpg", "media_type": "image"},
            format="json",
        )
        request.user = MagicMock()
        request.user.is_authenticated = True
        request.user.id = uuid.uuid4()
        request.auth = MagicMock()

        fake_media = MagicMock()
        fake_media.id = uuid.uuid4()
        fake_media.event_id = event_id
        fake_media.url = "http://example.com/img.jpg"
        fake_media.media_type = "image"
        fake_media.caption = ""
        fake_media.position = 0
        fake_media.thumbnail_urls = {}
        fake_media.created_at = datetime.datetime.now(datetime.timezone.utc)

        with (
            patch("rest_framework.views.APIView.perform_authentication"),
            patch("rest_framework.views.APIView.check_permissions"),
            patch.object(EventMedia.objects, "filter") as mock_filter,
            patch.object(EventMedia.objects, "create") as mock_create,
        ):
            count_qs = MagicMock()
            count_qs.count.return_value = 5
            mock_filter.return_value = count_qs
            mock_create.return_value = fake_media

            view = EventMediaListCreateView.as_view()
            response = view(request, event_id=event_id)

        # must not be blocked by the limit (201 = created)
        assert response.status_code == 201
