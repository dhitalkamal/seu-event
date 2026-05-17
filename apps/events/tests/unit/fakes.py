"""Hand-rolled in-memory fakes for all repository interfaces."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from apps.events.domain.entities import EventEntity
from apps.events.domain.repositories import IEventRepository


def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_event(**kwargs: object) -> EventEntity:
    """Build an EventEntity with sensible defaults for testing."""
    now = _now()
    defaults: dict = {
        "id": uuid.uuid4(),
        "organiser_id": uuid.uuid4(),
        "title": "Test Event",
        "description": "A test event description.",
        "location": "Kathmandu, Nepal",
        "start_date": now + timedelta(days=7),
        "end_date": now + timedelta(days=8),
        "capacity": 100,
        "registered_count": 0,
        "status": "draft",
        "visibility": "public",
        "is_free": True,
        "price": Decimal("0.00"),
        "created_at": now,
        "updated_at": now,
        "deleted_at": None,
    }
    defaults.update(kwargs)
    return EventEntity(**defaults)  # type: ignore[arg-type]


class FakeEventRepository(IEventRepository):
    """In-memory event store backed by a dict keyed on event.id."""

    def __init__(self, events: list[EventEntity] | None = None) -> None:
        self._store: dict[uuid.UUID, EventEntity] = {e.id: e for e in (events or [])}

    def create(self, entity: EventEntity) -> EventEntity:
        """Persist the entity and return it."""
        self._store[entity.id] = entity
        return entity
