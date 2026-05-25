"""Use case: transition an event from DRAFT to PUBLISHED."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from apps.events.domain.entities import EventEntity
from apps.events.domain.exceptions import (
    EventDateError,
    EventNotOwnedError,
    InvalidEventStatusTransitionError,
)
from apps.events.domain.repositories import IEventRepository, IEventSearchIndex


class PublishEventUseCase:
    """Publish a draft event after validating ownership and timing."""

    # ! only DRAFT events may be published
    _ALLOWED_FROM: frozenset[str] = frozenset({"draft"})

    def __init__(
        self,
        event_repo: IEventRepository,
        search_index: IEventSearchIndex | None = None,
    ) -> None:
        self._events = event_repo
        self._index = search_index

    def execute(self, *, event_id: uuid.UUID, organiser_id: uuid.UUID) -> EventEntity:
        """
        Validate ownership and state, then set status to published.

        @param event_id - the event to publish
        @param organiser_id - UUID from the JWT; must match event.organiser_id
        @raises EventNotOwnedError if the requester is not the organiser
        @raises InvalidEventStatusTransitionError if the event is not in DRAFT
        @raises EventDateError if start_date has already passed
        """
        event = self._events.get_by_id(event_id)

        if event.organiser_id != organiser_id:
            raise EventNotOwnedError("You are not the organiser of this event.")

        if event.status not in self._ALLOWED_FROM:
            raise InvalidEventStatusTransitionError(f"Cannot publish an event with status '{event.status}'.")

        if event.start_date <= datetime.now(timezone.utc):
            raise EventDateError("Cannot publish an event whose start date has already passed.")

        event.status = "published"
        event.updated_at = datetime.now(timezone.utc)
        saved = self._events.update(event)
        if self._index is not None:
            self._index.index_event(saved)
        return saved
