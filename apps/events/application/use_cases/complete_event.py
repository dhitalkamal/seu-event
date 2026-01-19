"""Use case: transition an event from PUBLISHED to COMPLETED."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from apps.events.domain.entities import EventEntity
from apps.events.domain.exceptions import EventNotOwnedError, InvalidEventStatusTransitionError
from apps.events.domain.repositories import IEventRepository


class CompleteEventUseCase:
    """Mark a published event as completed after it has taken place."""

    # ! only PUBLISHED events may be completed
    _ALLOWED_FROM: frozenset[str] = frozenset({"published"})

    def __init__(self, event_repo: IEventRepository) -> None:
        self._events = event_repo

    def execute(self, *, event_id: uuid.UUID, organiser_id: uuid.UUID) -> EventEntity:
        """
        Validate ownership and state, then set status to completed.

        @param event_id - the event to complete
        @param organiser_id - UUID from the JWT; must match event.organiser_id
        @raises EventNotOwnedError if the requester is not the organiser
        @raises InvalidEventStatusTransitionError if the event is not PUBLISHED
        """
        event = self._events.get_by_id(event_id)

        if event.organiser_id != organiser_id:
            raise EventNotOwnedError("You are not the organiser of this event.")

        if event.status not in self._ALLOWED_FROM:
            raise InvalidEventStatusTransitionError(f"Cannot complete an event with status '{event.status}'.")

        event.status = "completed"
        event.updated_at = datetime.now(timezone.utc)
        return self._events.update(event)
