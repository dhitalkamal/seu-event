"""Use case: list published public events with optional filters."""

from __future__ import annotations

import uuid

from apps.events.domain.entities import EventEntity
from apps.events.domain.repositories import IEventRepository


class ListEventsUseCase:
    """Return published public events, applying any provided filters."""

    def __init__(self, event_repo: IEventRepository) -> None:
        self._events = event_repo

    def execute(
        self,
        *,
        organiser_id: uuid.UUID | None = None,
        is_free: bool | None = None,
        search: str | None = None,
    ) -> list[EventEntity]:
        """Delegate filtering to the repository and return the matching events."""
        return self._events.list_public(
            organiser_id=organiser_id,
            is_free=is_free,
            search=search,
        )
