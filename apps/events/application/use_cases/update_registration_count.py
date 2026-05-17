"""Use case: atomically update an event's registered_count."""

from __future__ import annotations

import uuid

from apps.events.domain.repositories import IEventRepository


class UpdateRegistrationCountUseCase:
    """Increment or decrement registered_count; never let it go below zero."""

    def __init__(self, event_repo: IEventRepository) -> None:
        self._events = event_repo

    def execute(self, *, event_id: uuid.UUID, delta: int) -> None:
        """
        Apply delta (+1 or -1) to the event's registered_count.

        @param event_id - the event to update
        @param delta - +1 for a new registration, -1 for a cancellation
        @raises EventNotFoundError if the event does not exist
        """
        event = self._events.get_by_id(event_id)
        event.registered_count = max(0, event.registered_count + delta)
        self._events.update(event)
