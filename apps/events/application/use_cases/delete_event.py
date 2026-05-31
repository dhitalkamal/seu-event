"""Use case: soft-delete an event by setting deleted_at and status to cancelled."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from apps.events.domain.exceptions import EventNotOwnedError
from apps.events.domain.repositories import IEventRepository


class DeleteEventUseCase:
    """Soft-delete an event owned by the given organizer."""

    def __init__(self, event_repo: IEventRepository) -> None:
        self._events = event_repo

    def execute(self, *, event_id: uuid.UUID, organizer_id: uuid.UUID) -> None:
        """
        Set deleted_at and status=cancelled on the event.

        @param event_id - the event to delete
        @param organizer_id - UUID from JWT; must match event.organizer_id
        @raises EventNotOwnedError if the requester is not the organizer
        """
        event = self._events.get_by_id(event_id)

        if event.organizer_id != organizer_id:
            raise EventNotOwnedError("You are not the organizer of this event.")

        now = datetime.now(timezone.utc)
        event.deleted_at = now
        event.status = "cancelled"
        event.updated_at = now
        self._events.update(event)
