"""Use case: transition an event from DRAFT to PUBLISHED."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

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
        redis_client: Any | None = None,
    ) -> None:
        self._events = event_repo
        self._index = search_index
        self._redis = redis_client

    def execute(self, *, event_id: uuid.UUID, organizer_id: uuid.UUID) -> EventEntity:
        """
        Validate ownership and state, then set status to published.

        Also seeds the Redis capacity counter so participation-service can
        do fast capacity checks without hitting the DB.

        @param event_id - the event to publish
        @param organizer_id - UUID from the JWT; must match event.organizer_id
        @raises EventNotOwnedError if the requester is not the organizer
        @raises InvalidEventStatusTransitionError if the event is not in DRAFT
        @raises EventDateError if start_date has already passed
        """
        event = self._events.get_by_id(event_id)

        if event.organizer_id != organizer_id:
            raise EventNotOwnedError("You are not the organizer of this event.")

        if event.status not in self._ALLOWED_FROM:
            raise InvalidEventStatusTransitionError(f"Cannot publish an event with status '{event.status}'.")

        if event.start_date <= datetime.now(timezone.utc):
            raise EventDateError("Cannot publish an event whose start date has already passed.")

        event.status = "published"
        event.updated_at = datetime.now(timezone.utc)
        saved = self._events.update(event)

        if self._index is not None:
            self._index.index_event(saved)

        # seed Redis capacity counter for fast-path checks in participation-service
        if self._redis is not None:
            from apps.events.infrastructure.capacity import init_capacity_counter

            init_capacity_counter(event=saved, redis_client=self._redis)

        return saved
