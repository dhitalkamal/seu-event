"""Concrete repository implementations backed by the Django ORM."""

from __future__ import annotations

from apps.events.domain.entities import EventEntity
from apps.events.domain.repositories import IEventRepository
from apps.events.infrastructure.models import Event


class DjangoEventRepository(IEventRepository):
    """Persists Event entities using the Django ORM."""

    def create(self, entity: EventEntity) -> EventEntity:
        """Persist a new event and return the saved entity."""
        obj = Event.from_entity(entity)
        obj.save(using="default")
        return obj.to_entity()
