"""Use case: create a new event in DRAFT status."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from apps.events.domain.entities import EventEntity
from apps.events.domain.exceptions import EventDateError
from apps.events.domain.repositories import ICategoryRepository, IEventRepository, ITagRepository


class CreateEventUseCase:
    """Create a new event owned by the given organizer."""

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
        organizer_id: uuid.UUID,
        title: str,
        description: str,
        location: str,
        start_date: datetime,
        end_date: datetime,
        capacity: int,
        visibility: str,
        is_free: bool,
        price: Decimal | None = None,
        cover_image: str | None = None,
        is_online: bool = False,
        category_id: uuid.UUID | None = None,
        tag_ids: list[uuid.UUID] | None = None,
        allowed_domains: list[str] | None = None,
        organization_id: uuid.UUID | None = None,
        venue_id: uuid.UUID | None = None,
        latitude: Decimal | None = None,
        longitude: Decimal | None = None,
        event_mode: str = "physical",
        virtual_capacity: int | None = None,
        overbooking_percent: int = 0,
    ) -> EventEntity:
        """
        Validate dates, category, tags, apply pricing rule, and persist the event.

        @param organizer_id - UUID from the JWT, never a DB FK
        @param title - event name
        @param description - full event description
        @param location - physical or virtual location string
        @param start_date - event start (timezone-aware)
        @param end_date - event end, must be strictly after start_date
        @param capacity - maximum number of attendees
        @param visibility - public | private | unlisted
        @param is_free - True means price is forced to 0.00
        @param price - ticket price in NPR; ignored when is_free is True
        @param category_id - optional FK to a Category
        @param tag_ids - optional list of Tag UUIDs to attach
        @param venue_id - optional UUID reference to management-service venue
        @param latitude - optional decimal latitude (client-side geocoded)
        @param longitude - optional decimal longitude (client-side geocoded)
        @returns the persisted EventEntity with status=DRAFT
        @raises EventDateError if end_date <= start_date
        @raises CategoryNotFoundError if category_id does not exist
        @raises TagNotFoundError if any tag_id does not exist
        """
        if end_date <= start_date:
            raise EventDateError("end_date must be strictly after start_date.")

        if category_id is not None:
            # ! validates existence; raises CategoryNotFoundError when absent
            if self._categories is None:
                from apps.events.infrastructure.repositories import DjangoCategoryRepository

                self._categories = DjangoCategoryRepository()
            self._categories.get_by_id(category_id)

        resolved_tag_ids: list[uuid.UUID] = []
        if tag_ids:
            if self._tags is None:
                from apps.events.infrastructure.repositories import DjangoTagRepository

                self._tags = DjangoTagRepository()
            for tid in tag_ids:
                self._tags.get_by_id(tid)
                self._tags.increment_usage(tid)
                resolved_tag_ids.append(tid)

        # * free events always have zero price regardless of submitted value
        effective_price = Decimal("0.00") if is_free else (price or Decimal("0.00"))

        now = datetime.now(timezone.utc)
        entity = EventEntity(
            id=uuid.uuid4(),
            organizer_id=organizer_id,
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
            category_id=category_id,
            tag_ids=resolved_tag_ids,
            allowed_domains=[d.lower().strip() for d in (allowed_domains or []) if d.strip()],
            organization_id=organization_id,
            venue_id=venue_id,
            latitude=latitude,
            longitude=longitude,
            event_mode=event_mode,
            virtual_capacity=virtual_capacity,
            overbooking_percent=overbooking_percent,
        )
        return self._events.create(entity)
