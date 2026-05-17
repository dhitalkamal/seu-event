"""Concrete repository implementations backed by the Django ORM."""

from __future__ import annotations

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
