"""Hand-rolled in-memory fakes for all repository interfaces."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from apps.events.domain.entities import CategoryEntity, EventEntity, TagEntity
from apps.events.domain.exceptions import (
    CategoryNotFoundError,
    EventNotFoundError,
    TagNotFoundError,
)
from apps.events.domain.repositories import (
    ICategoryRepository,
    IEventRepository,
    IEventSearchIndex,
    ITagRepository,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def make_event(**kwargs: object) -> EventEntity:
    """Build an EventEntity with sensible defaults for testing."""
    now = _now()
    defaults: dict = {
        "id": uuid.uuid4(),
        "organizer_id": uuid.uuid4(),
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
        organizer_id: uuid.UUID | None = None,
        is_free: bool | None = None,
        search: str | None = None,
        category_id: uuid.UUID | None = None,
        tag_id: uuid.UUID | None = None,
        date_from: object = None,
        date_to: object = None,
        location: str | None = None,
        user_email_domain: str | None = None,
    ) -> list[EventEntity]:
        """Return published public non-deleted events, applying optional filters."""
        results = [e for e in self._store.values() if e.status == "published" and e.visibility == "public" and e.deleted_at is None]
        # domain restriction: events with allowed_domains only visible to matching users
        results = [
            e
            for e in results
            if not e.allowed_domains
            or (user_email_domain is not None and user_email_domain.lower() in [d.lower() for d in e.allowed_domains])
        ]
        if organizer_id is not None:
            results = [e for e in results if e.organizer_id == organizer_id]
        if is_free is not None:
            results = [e for e in results if e.is_free == is_free]
        if search is not None:
            results = [e for e in results if search.lower() in e.title.lower()]
        if category_id is not None:
            results = [e for e in results if e.category_id == category_id]
        if tag_id is not None:
            results = [e for e in results if tag_id in (e.tag_ids or [])]
        if date_from is not None:
            results = [e for e in results if e.start_date >= date_from]
        if date_to is not None:
            results = [e for e in results if e.start_date <= date_to]
        if location is not None:
            results = [e for e in results if location.lower() in e.location.lower()]
        return results

    def list_by_organizer(self, organizer_id: uuid.UUID) -> list[EventEntity]:
        """Return all non-deleted events owned by the given organizer."""
        return [e for e in self._store.values() if e.organizer_id == organizer_id and e.deleted_at is None]


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


class FakeTagRepository(ITagRepository):
    """In-memory tag store backed by a dict keyed on tag.id."""

    def __init__(self, tags: list[TagEntity] | None = None) -> None:
        self._store: dict[uuid.UUID, TagEntity] = {t.id: t for t in (tags or [])}

    def create(self, entity: TagEntity) -> TagEntity:
        """Persist the entity and return it."""
        self._store[entity.id] = entity
        return entity

    def get_by_slug(self, slug: str) -> TagEntity | None:
        """Return the tag matching slug, or None if absent."""
        return next((t for t in self._store.values() if t.slug == slug), None)

    def get_by_id(self, tag_id: uuid.UUID) -> TagEntity:
        """Return the tag or raise TagNotFoundError."""
        entity = self._store.get(tag_id)
        if entity is None:
            raise TagNotFoundError("Tag not found.")
        return entity

    def increment_usage(self, tag_id: uuid.UUID) -> None:
        """Increment usage_count on the stored tag in place."""
        tag = self.get_by_id(tag_id)
        self._store[tag_id] = TagEntity(
            id=tag.id,
            name=tag.name,
            slug=tag.slug,
            usage_count=tag.usage_count + 1,
        )

    def list_all(self) -> list[TagEntity]:
        """Return all stored tags."""
        return list(self._store.values())


class FakeEventSearchIndex(IEventSearchIndex):
    """In-memory event search index for unit tests."""

    def __init__(self) -> None:
        self.indexed: list[EventEntity] = []
        self.deleted: list[uuid.UUID] = []

    def index_event(self, entity: EventEntity) -> None:
        """Record the event as indexed."""
        self.indexed.append(entity)

    def delete_event(self, event_id: uuid.UUID) -> None:
        """Record the event_id as deleted from the index."""
        self.deleted.append(event_id)
