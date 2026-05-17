"""Use case: fetch a single event by id."""

from __future__ import annotations

import uuid

from apps.events.domain.entities import EventEntity
from apps.events.domain.repositories import IEventRepository


class GetEventUseCase:
    """Fetch an event by its primary key."""

    def __init__(self, event_repo: IEventRepository) -> None:
        self._events = event_repo

    def execute(self, *, event_id: uuid.UUID) -> EventEntity:
        """Return the event or raise EventNotFoundError if absent or soft-deleted."""
        return self._events.get_by_id(event_id)
