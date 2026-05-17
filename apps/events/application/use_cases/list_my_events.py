"""Use case: list the authenticated organiser's own events."""

from __future__ import annotations

import uuid

from apps.events.domain.entities import EventEntity
from apps.events.domain.repositories import IEventRepository


class ListMyEventsUseCase:
    """Return all non-deleted events owned by the given organiser."""

    def __init__(self, event_repo: IEventRepository) -> None:
        self._events = event_repo

    def execute(self, *, organiser_id: uuid.UUID) -> list[EventEntity]:
        """Return events across all statuses except soft-deleted."""
        return self._events.list_by_organiser(organiser_id)
