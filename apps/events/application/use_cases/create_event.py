"""Use case: create a new event in DRAFT status."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from apps.events.domain.entities import EventEntity
from apps.events.domain.exceptions import EventDateError
from apps.events.domain.repositories import IEventRepository


class CreateEventUseCase:
    """Create a new event owned by the given organiser."""

    def __init__(self, event_repo: IEventRepository) -> None:
        self._events = event_repo

    def execute(
        self,
        *,
        organiser_id: uuid.UUID,
        title: str,
        description: str,
        location: str,
        start_date: datetime,
        end_date: datetime,
        capacity: int,
        visibility: str,
        is_free: bool,
        price: Decimal | None,
        cover_image: str | None = None,
        is_online: bool = False,
    ) -> EventEntity:
        """
        Validate dates, apply pricing rule, and persist the event.

        @param organiser_id - UUID from the JWT, never a DB FK
        @param title - event name
        @param description - full event description
        @param location - physical or virtual location string
        @param start_date - event start (timezone-aware)
        @param end_date - event end, must be strictly after start_date
        @param capacity - maximum number of attendees
        @param visibility - public | private | unlisted
        @param is_free - True means price is forced to 0.00
        @param price - ticket price in NPR; ignored when is_free is True
        @returns the persisted EventEntity with status=DRAFT
        @raises EventDateError if end_date <= start_date
        """
        if end_date <= start_date:
            raise EventDateError("end_date must be strictly after start_date.")

        # * free events always have zero price regardless of submitted value
        effective_price = Decimal("0.00") if is_free else (price or Decimal("0.00"))

        now = datetime.now(timezone.utc)
        entity = EventEntity(
            id=uuid.uuid4(),
            organiser_id=organiser_id,
            title=title,
            description=description,
            location=location,
            start_date=start_date,
            end_date=end_date,
            capacity=capacity,
            registered_count=0,
            status="draft",
            visibility=visibility,
            is_free=is_free,
            price=effective_price,
            created_at=now,
            updated_at=now,
            cover_image=cover_image,
            is_online=is_online,
        )
        return self._events.create(entity)
