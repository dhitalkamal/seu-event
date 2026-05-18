"""DRF serializers for events request deserialization and response shaping."""

from __future__ import annotations

from rest_framework import serializers


class CreateEventSerializer(serializers.Serializer):
    """Payload for creating a new event."""

    title = serializers.CharField(max_length=255)
    description = serializers.CharField()
    location = serializers.CharField(max_length=500)
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    capacity = serializers.IntegerField(min_value=1)
    visibility = serializers.ChoiceField(
        choices=["public", "private", "unlisted"],
        default="public",
    )
    is_free = serializers.BooleanField(default=True)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, default="0.00")
    cover_image = serializers.URLField(max_length=2048, required=False, allow_null=True)
    is_online = serializers.BooleanField(default=False)
    online_url = serializers.URLField(max_length=2048, required=False, allow_null=True)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    tag_ids = serializers.ListField(child=serializers.UUIDField(), required=False, default=list)
    # primary USP: list of email domains; empty means no restriction
    allowed_domains = serializers.ListField(
        child=serializers.CharField(max_length=253), required=False, default=list
    )


class UpdateEventSerializer(serializers.Serializer):
    """Partial-update payload: every field is optional."""

    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False)
    location = serializers.CharField(max_length=500, required=False)
    start_date = serializers.DateTimeField(required=False)
    end_date = serializers.DateTimeField(required=False)
    capacity = serializers.IntegerField(min_value=1, required=False)
    visibility = serializers.ChoiceField(
        choices=["public", "private", "unlisted"],
        required=False,
    )
    is_free = serializers.BooleanField(required=False)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    cover_image = serializers.URLField(max_length=2048, required=False, allow_null=True)
    is_online = serializers.BooleanField(required=False)
    online_url = serializers.URLField(max_length=2048, required=False, allow_null=True)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    tag_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    allowed_domains = serializers.ListField(
        child=serializers.CharField(max_length=253), required=False
    )


class EventMediaSerializer(serializers.Serializer):
    """Request body for adding a gallery image or video."""

    url = serializers.URLField(max_length=2048)
    media_type = serializers.ChoiceField(choices=["image", "video"], default="image")
    caption = serializers.CharField(max_length=255, required=False, default="")
    position = serializers.IntegerField(min_value=0, required=False, default=0)


class EventMediaResponseSerializer(serializers.Serializer):
    """Public shape of an event media item."""

    id = serializers.UUIDField()
    event_id = serializers.UUIDField(source="event.id")
    url = serializers.URLField()
    media_type = serializers.CharField()
    caption = serializers.CharField()
    position = serializers.IntegerField()
    created_at = serializers.DateTimeField()


class EventFilterSerializer(serializers.Serializer):
    """Query parameter validator for the public event list endpoint."""

    organiser_id = serializers.UUIDField(required=False)
    category_id = serializers.UUIDField(required=False)
    tag_id = serializers.UUIDField(required=False)
    # NullBooleanField used intentionally: BooleanField treats a missing
    # QueryDict key as False (HTML checkbox semantics), which would silently
    # filter out all free events when no is_free param is provided.
    is_free = serializers.BooleanField(required=False, allow_null=True)
    search = serializers.CharField(required=False, max_length=255)
    location = serializers.CharField(required=False, max_length=255)
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)


class CreateCategorySerializer(serializers.Serializer):
    """Payload for creating a new category."""

    name = serializers.CharField(max_length=100)
    slug = serializers.SlugField(max_length=120)
    parent_id = serializers.UUIDField(required=False, allow_null=True)


class CategoryResponseSerializer(serializers.Serializer):
    """Public shape of a category resource."""

    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    parent_id = serializers.UUIDField(allow_null=True)
    depth = serializers.IntegerField()


class CreateTagSerializer(serializers.Serializer):
    """Payload for creating a new tag."""

    name = serializers.CharField(max_length=100)
    slug = serializers.SlugField(max_length=120)


class TagResponseSerializer(serializers.Serializer):
    """Public shape of a tag resource."""

    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    usage_count = serializers.IntegerField()


class RegistrationCountSerializer(serializers.Serializer):
    """Payload for incrementing or decrementing registered_count."""

    delta = serializers.IntegerField()


class EventResponseSerializer(serializers.Serializer):
    """Public shape of an event resource returned by the API."""

    id = serializers.UUIDField()
    organiser_id = serializers.UUIDField()
    title = serializers.CharField()
    description = serializers.CharField()
    location = serializers.CharField()
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    capacity = serializers.IntegerField()
    registered_count = serializers.IntegerField()
    status = serializers.CharField()
    visibility = serializers.CharField()
    is_free = serializers.BooleanField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    cover_image = serializers.URLField(allow_null=True)
    is_online = serializers.BooleanField()
    online_url = serializers.URLField(allow_null=True)
    category_id = serializers.UUIDField(allow_null=True)
    tag_ids = serializers.ListField(child=serializers.UUIDField())
    allowed_domains = serializers.ListField(child=serializers.CharField())
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
