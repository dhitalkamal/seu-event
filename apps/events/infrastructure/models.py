"""Django ORM models for the events domain. Maps domain entities to the events schema."""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import models

from apps.events.domain.entities import CategoryEntity, EventEntity, TagEntity


class Tag(models.Model):
    """Free-form label that can be attached to events."""

    class Meta:
        db_table = "events_tag"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    usage_count = models.PositiveIntegerField(default=0)

    def to_entity(self) -> TagEntity:
        """Map this ORM row to a TagEntity."""
        return TagEntity(
            id=self.id,
            name=self.name,
            slug=self.slug,
            usage_count=self.usage_count,
        )

    @classmethod
    def from_entity(cls, entity: TagEntity) -> "Tag":
        """Build an unsaved ORM instance from a TagEntity."""
        return cls(
            id=entity.id,
            name=entity.name,
            slug=entity.slug,
            usage_count=entity.usage_count,
        )


class Category(models.Model):
    """Hierarchical event category. Self-referential FK; max 3 levels deep."""

    class Meta:
        db_table = "events_category"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    depth = models.PositiveSmallIntegerField(default=0)

    def to_entity(self) -> CategoryEntity:
        """Map this ORM row to a CategoryEntity."""
        return CategoryEntity(
            id=self.id,
            name=self.name,
            slug=self.slug,
            parent_id=self.parent_id,
            depth=self.depth,
        )

    @classmethod
    def from_entity(cls, entity: CategoryEntity) -> "Category":
        """Build an unsaved ORM instance from a CategoryEntity."""
        return cls(
            id=entity.id,
            name=entity.name,
            slug=entity.slug,
            parent_id=entity.parent_id,
            depth=entity.depth,
        )


class Event(models.Model):
    """Platform event. Owned by an organizer identified by organizer_id from JWT."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"
        UNLISTED = "unlisted", "Unlisted"

    class EventMode(models.TextChoices):
        PHYSICAL = "physical", "Physical"
        VIRTUAL = "virtual", "Virtual"
        HYBRID = "hybrid", "Hybrid"

    class Meta:
        db_table = "events_event"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizer_id = models.UUIDField()
    # optional: event belongs to an organization (null for individually-owned events)
    organization_id = models.UUIDField(null=True, blank=True, db_index=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    location = models.CharField(max_length=500)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    capacity = models.PositiveIntegerField()
    registered_count = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.PUBLIC)
    is_free = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    cover_image = models.URLField(max_length=2048, null=True, blank=True)
    is_online = models.BooleanField(default=False)
    online_url = models.URLField(max_length=2048, null=True, blank=True)
    # event_mode supersedes is_online for new events
    event_mode = models.CharField(
        max_length=20,
        choices=EventMode.choices,
        default=EventMode.PHYSICAL,
    )
    # extra capacity for hybrid events (online attendees)
    virtual_capacity = models.PositiveIntegerField(null=True, blank=True)
    # allow registrations beyond capacity by this percentage (0 = strict)
    overbooking_percent = models.PositiveSmallIntegerField(default=0)
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="events")
    # primary USP: empty list means no restriction
    allowed_domains = models.JSONField(default=list, blank=True)
    # null when the event is not part of a recurrence series
    parent_event_id = models.UUIDField(null=True, blank=True)
    # venue reference: nullable UUID pointing to a venue in management-service
    venue_id = models.UUIDField(null=True, blank=True, db_index=True)
    # coordinates supplied by client-side geocoding (we never call a geocoding API)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    waitlist_enabled = models.BooleanField(default=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def to_entity(self) -> EventEntity:
        """Map this ORM row to a pure-Python EventEntity."""
        return EventEntity(
            id=self.id,
            organizer_id=self.organizer_id,
            organization_id=self.organization_id,
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
            cover_image=self.cover_image,
            is_online=self.is_online,
            online_url=self.online_url,
            category_id=self.category_id,
            tag_ids=[t.id for t in self.tags.all()],
            allowed_domains=self.allowed_domains or [],
            created_at=self.created_at,
            updated_at=self.updated_at,
            deleted_at=self.deleted_at,
            parent_event_id=self.parent_event_id,
            venue_id=self.venue_id,
            latitude=self.latitude,
            longitude=self.longitude,
            event_mode=self.event_mode,
            virtual_capacity=self.virtual_capacity,
            overbooking_percent=self.overbooking_percent,
            waitlist_enabled=self.waitlist_enabled,
        )

    @classmethod
    def from_entity(cls, entity: EventEntity) -> "Event":
        """Build an unsaved ORM instance from an EventEntity."""
        return cls(
            id=entity.id,
            organizer_id=entity.organizer_id,
            organization_id=entity.organization_id,
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
            cover_image=entity.cover_image,
            is_online=entity.is_online,
            online_url=entity.online_url,
            category_id=entity.category_id,
            allowed_domains=entity.allowed_domains,
            deleted_at=entity.deleted_at,
            parent_event_id=entity.parent_event_id,
            venue_id=entity.venue_id,
            latitude=entity.latitude,
            longitude=entity.longitude,
            event_mode=entity.event_mode,
            virtual_capacity=entity.virtual_capacity,
            overbooking_percent=entity.overbooking_percent,
            waitlist_enabled=entity.waitlist_enabled,
        )


class EventMedia(models.Model):
    """Gallery image or video attached to an event."""

    class MediaType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"

    class Meta:
        db_table = "events_event_media"
        ordering = ["position"]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="media")
    url = models.URLField(max_length=2048)
    media_type = models.CharField(max_length=10, choices=MediaType.choices, default=MediaType.IMAGE)
    caption = models.CharField(max_length=255, blank=True, default="")
    position = models.PositiveSmallIntegerField(default=0)
    # keys are "{w}x{h}" e.g. "200x200", "400x400", "800x800"
    thumbnail_urls = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
