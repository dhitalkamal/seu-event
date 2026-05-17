"""Django ORM models for the events domain. Maps domain entities to the events schema."""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import models

from apps.events.domain.entities import EventEntity


class Event(models.Model):
    """Platform event. Owned by an organiser identified by organiser_id from JWT."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"
        UNLISTED = "unlisted", "Unlisted"

    class Meta:
        db_table = '"events"."event"'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organiser_id = models.UUIDField()
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=500)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    registered_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC
    )
    is_free = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_entity(self) -> EventEntity:
        """Map this ORM row to a pure-Python EventEntity."""
        return EventEntity(
            id=self.id,
            organiser_id=self.organiser_id,
            title=self.title,
            description=self.description,
            location=self.location,
            start_date=self.start_date,
            end_date=self.end_date,
            capacity=self.capacity,
            registered_count=self.registered_count,
            status=self.status,
            visibility=self.visibility,
            is_free=self.is_free,
            price=self.price,
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
        )

    @classmethod
    def from_entity(cls, entity: EventEntity) -> "Event":
        """Build an unsaved ORM instance from an EventEntity."""
        return cls(
            id=entity.id,
            organiser_id=entity.organiser_id,
            title=entity.title,
            description=entity.description,
            location=entity.location,
            start_date=entity.start_date,
            end_date=entity.end_date,
            capacity=entity.capacity,
            registered_count=entity.registered_count,
            status=entity.status,
            visibility=entity.visibility,
            is_free=entity.is_free,
            price=entity.price,
            deleted_at=entity.deleted_at,
        )
