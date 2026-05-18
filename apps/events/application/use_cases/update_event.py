"""Use case: partially update an event's fields."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from apps.events.domain.entities import EventEntity
from apps.events.domain.exceptions import EventDateError, EventNotOwnedError
from apps.events.domain.repositories import ICategoryRepository, IEventRepository, ITagRepository


class UpdateEventUseCase:
    """Apply a partial update to an event owned by the given organiser."""

    def __init__(
        self,
        event_repo: IEventRepository,
        category_repo: ICategoryRepository | None = None,
        tag_repo: ITagRepository | None = None,
    ) -> None:
        self._events = event_repo
        self._categories = category_repo
        self._tags = tag_repo

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
        category_id: uuid.UUID | None = None,
        tag_ids: list[uuid.UUID] | None = None,
        allowed_domains: list[str] | None = None,
    ) -> EventEntity:
        """
        Apply only the provided (non-None) fields and persist.

        @param event_id - the event to update
        @param organiser_id - UUID from JWT; must match event.organiser_id
        @raises EventNotOwnedError if the requester is not the organiser
        @raises EventDateError if the updated dates are logically invalid
        @raises CategoryNotFoundError if category_id does not exist
        @raises TagNotFoundError if any tag_id does not exist
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

        if category_id is not None:
            if self._categories is None:
                from apps.events.infrastructure.repositories import DjangoCategoryRepository

                self._categories = DjangoCategoryRepository()
            self._categories.get_by_id(category_id)
            event.category_id = category_id

        if tag_ids is not None:
            if self._tags is None:
                from apps.events.infrastructure.repositories import DjangoTagRepository

                self._tags = DjangoTagRepository()
            for tid in tag_ids:
                self._tags.get_by_id(tid)
                self._tags.increment_usage(tid)
            event.tag_ids = list(tag_ids)

        if allowed_domains is not None:
            event.allowed_domains = [d.lower().strip() for d in allowed_domains if d.strip()]

        event.updated_at = datetime.now(timezone.utc)
        return self._events.update(event)
