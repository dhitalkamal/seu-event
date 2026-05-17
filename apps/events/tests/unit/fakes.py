"""Hand-rolled in-memory fakes for all repository interfaces."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from apps.events.domain.entities import CategoryEntity, EventEntity
from apps.events.domain.exceptions import CategoryNotFoundError, EventNotFoundError
from apps.events.domain.repositories import ICategoryRepository, IEventRepository


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

    def get_by_id(self, event_id: uuid.UUID) -> EventEntity:
        """Return the event or raise EventNotFoundError. Excludes soft-deleted events."""
        entity = self._store.get(event_id)
        if entity is None or entity.deleted_at is not None:
            raise EventNotFoundError("Event not found.")
        return entity

    def update(self, entity: EventEntity) -> EventEntity:
        """Overwrite the stored entity and return it."""
        self._store[entity.id] = entity
        return entity

    def list_public(
        self,
        *,
        organiser_id: uuid.UUID | None = None,
        is_free: bool | None = None,
        search: str | None = None,
    ) -> list[EventEntity]:
        """Return published public non-deleted events, applying optional filters."""
        results = [
            e
            for e in self._store.values()
            if e.status == "published" and e.visibility == "public" and e.deleted_at is None
        ]
        if organiser_id is not None:
            results = [e for e in results if e.organiser_id == organiser_id]
        if is_free is not None:
            results = [e for e in results if e.is_free == is_free]
        if search is not None:
            results = [e for e in results if search.lower() in e.title.lower()]
        return results

    def list_by_organiser(self, organiser_id: uuid.UUID) -> list[EventEntity]:
        """Return all non-deleted events owned by the given organiser."""
        return [
            e
            for e in self._store.values()
            if e.organiser_id == organiser_id and e.deleted_at is None
        ]


class FakeCategoryRepository(ICategoryRepository):
    """In-memory category store backed by a dict keyed on category.id."""

    def __init__(self, categories: list[CategoryEntity] | None = None) -> None:
        self._store: dict[uuid.UUID, CategoryEntity] = {c.id: c for c in (categories or [])}

    def create(self, entity: CategoryEntity) -> CategoryEntity:
        """Persist the entity and return it."""
        self._store[entity.id] = entity
        return entity

    def get_by_id(self, category_id: uuid.UUID) -> CategoryEntity:
        """Return the category or raise CategoryNotFoundError."""
        entity = self._store.get(category_id)
        if entity is None:
            raise CategoryNotFoundError("Category not found.")
        return entity

    def list_all(self) -> list[CategoryEntity]:
        """Return all stored categories."""
        return list(self._store.values())
