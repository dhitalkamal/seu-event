"""Concrete repository implementations backed by the Django ORM."""

from __future__ import annotations

import uuid

from apps.events.domain.entities import EventEntity
from apps.events.domain.exceptions import EventNotFoundError
from apps.events.domain.repositories import IEventRepository
from apps.events.infrastructure.models import Event


class DjangoEventRepository(IEventRepository):
    """Persists Event entities using the Django ORM."""

    def create(self, entity: EventEntity) -> EventEntity:
        """Persist a new event and return the saved entity."""
        obj = Event.from_entity(entity)
        obj.save(using="default")
        return obj.to_entity()

    def get_by_id(self, event_id: object) -> EventEntity:
        """Fetch by id, excluding soft-deleted rows. Raises EventNotFoundError if absent."""
        try:
            return Event.objects.get(id=event_id, deleted_at__isnull=True).to_entity()
        except Event.DoesNotExist:
            raise EventNotFoundError("Event not found.")

    def update(self, entity: EventEntity) -> EventEntity:
        """Fetch the existing row, update all mutable fields, and save."""
        obj = Event.objects.get(id=entity.id)
        obj.title = entity.title
        obj.description = entity.description
        obj.location = entity.location
        obj.start_date = entity.start_date
        obj.end_date = entity.end_date
        obj.capacity = entity.capacity
        obj.status = entity.status
        obj.visibility = entity.visibility
        obj.is_free = entity.is_free
        obj.price = entity.price
        obj.deleted_at = entity.deleted_at
        obj.save()
        return obj.to_entity()

    def list_public(
        self,
        *,
        organiser_id: uuid.UUID | None = None,
        is_free: bool | None = None,
        search: str | None = None,
    ) -> list[EventEntity]:
        """Return published public non-deleted events, applying optional filters."""
        qs = Event.objects.filter(
            status="published",
            visibility="public",
            deleted_at__isnull=True,
        )
        if organiser_id is not None:
            qs = qs.filter(organiser_id=organiser_id)
        if is_free is not None:
            qs = qs.filter(is_free=is_free)
        if search is not None:
            qs = qs.filter(title__icontains=search)
        return [obj.to_entity() for obj in qs.order_by("-created_at")]

    def list_by_organiser(self, organiser_id: uuid.UUID) -> list[EventEntity]:
        """Return all non-deleted events owned by the organiser across all statuses."""
        return [
            obj.to_entity()
            for obj in Event.objects.filter(
                organiser_id=organiser_id,
                deleted_at__isnull=True,
            ).order_by("-created_at")
        ]
