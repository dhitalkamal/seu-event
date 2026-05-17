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
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
