"""Use case: partially update an event's fields."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from apps.events.domain.entities import EventEntity
from apps.events.domain.exceptions import EventDateError, EventNotOwnedError
from apps.events.domain.repositories import IEventRepository


class UpdateEventUseCase:
    """Apply a partial update to an event owned by the given organiser."""

    def __init__(self, event_repo: IEventRepository) -> None:
        self._events = event_repo

    def execute(
        self,
        *,
        event_id: uuid.UUID,
        organiser_id: uuid.UUID,
        title: str | None = None,
        description: str | None = None,
        location: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        capacity: int | None = None,
        visibility: str | None = None,
        is_free: bool | None = None,
        price: Decimal | None = None,
        cover_image: str | None = None,
        is_online: bool | None = None,
    ) -> EventEntity:
        """
        Apply only the provided (non-None) fields and persist.

        @param event_id - the event to update
        @param organiser_id - UUID from JWT; must match event.organiser_id
        @raises EventNotOwnedError if the requester is not the organiser
        @raises EventDateError if the updated dates are logically invalid
        """
        event = self._events.get_by_id(event_id)

        if event.organiser_id != organiser_id:
            raise EventNotOwnedError("You are not the organiser of this event.")

        if title is not None:
            event.title = title
        if description is not None:
            event.description = description
        if location is not None:
            event.location = location
        if capacity is not None:
            event.capacity = capacity
        if visibility is not None:
            event.visibility = visibility

        # * resolve effective dates before validating
        new_start = start_date if start_date is not None else event.start_date
        new_end = end_date if end_date is not None else event.end_date

        if start_date is not None or end_date is not None:
            if new_end <= new_start:
                raise EventDateError("end_date must be strictly after start_date.")

        event.start_date = new_start
        event.end_date = new_end

        if is_free is not None:
            event.is_free = is_free
            if is_free:
                event.price = Decimal("0.00")
        if price is not None and not event.is_free:
            event.price = price
        if cover_image is not None:
            event.cover_image = cover_image
        if is_online is not None:
            event.is_online = is_online

        event.updated_at = datetime.now(timezone.utc)
        return self._events.update(event)
