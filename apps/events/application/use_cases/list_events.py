"""Use case: list published public events with optional filters."""

from __future__ import annotations

import uuid
from datetime import datetime

from apps.events.domain.entities import EventEntity
from apps.events.domain.repositories import IEventRepository
from apps.events.infrastructure.haversine import haversine


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
        category_id: uuid.UUID | None = None,
        tag_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        location: str | None = None,
        user_email_domain: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
        radius_km: float | None = None,
        sort_by: str | None = None,
    ) -> list[EventEntity]:
        """Delegate filtering to the repository, apply location post-filter, and sort.

        @param lat - user latitude for proximity filtering
        @param lng - user longitude for proximity filtering
        @param radius_km - include only events within this radius (requires lat+lng)
        @param sort_by - one of date | popularity | distance
        @returns filtered and sorted list of EventEntity
        """
        events = self._events.list_public(
            organiser_id=organiser_id,
            is_free=is_free,
            search=search,
            category_id=category_id,
            tag_id=tag_id,
            date_from=date_from,
            date_to=date_to,
            location=location,
            user_email_domain=user_email_domain,
        )

        # * post-filter by radius if lat/lng provided; events without coordinates are excluded
        if lat is not None and lng is not None and radius_km is not None:
            filtered = []
            for ev in events:
                if ev.latitude is None or ev.longitude is None:
                    continue
                dist = haversine(lat, lng, float(ev.latitude), float(ev.longitude))
                if dist <= radius_km:
                    filtered.append(ev)
            events = filtered

        # * sort results; distance sort requires lat/lng
        if sort_by == "popularity":
            events = sorted(events, key=lambda e: e.registered_count, reverse=True)
        elif sort_by == "date":
            events = sorted(events, key=lambda e: e.start_date)
        elif sort_by == "distance" and lat is not None and lng is not None:
            events = sorted(
                events,
                key=lambda e: (
                    haversine(lat, lng, float(e.latitude), float(e.longitude))  # type: ignore[arg-type]
                    if e.latitude is not None and e.longitude is not None
                    else float("inf")
                ),
            )

        return events
