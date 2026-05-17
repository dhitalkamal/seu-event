"""Unit tests for wiring category_id and tags onto Event create/update."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from apps.events.application.use_cases.create_event import CreateEventUseCase
from apps.events.application.use_cases.update_event import UpdateEventUseCase
from apps.events.domain.entities import CategoryEntity, TagEntity
from apps.events.domain.exceptions import CategoryNotFoundError, TagNotFoundError
from apps.events.tests.unit.fakes import (
    FakeCategoryRepository,
    FakeEventRepository,
    FakeTagRepository,
    make_event,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_category(depth: int = 0) -> CategoryEntity:
    return CategoryEntity(id=uuid.uuid4(), name="Music", slug="music", depth=depth)


def _make_tag(name: str = "live") -> TagEntity:
    return TagEntity(id=uuid.uuid4(), name=name, slug=name.lower(), usage_count=0)


def _create(
    event_repo: FakeEventRepository,
    cat_repo: FakeCategoryRepository | None = None,
    tag_repo: FakeTagRepository | None = None,
    category_id: uuid.UUID | None = None,
    tag_ids: list[uuid.UUID] | None = None,
):
    """Helper: create a minimal event with optional category/tag overrides."""
    now = _now()
    return CreateEventUseCase(
        event_repo,
        category_repo=cat_repo or FakeCategoryRepository(),
        tag_repo=tag_repo or FakeTagRepository(),
    ).execute(
        organiser_id=uuid.uuid4(),
        title="Festival",
        description="Annual festival.",
        location="Pokhara",
        start_date=now + timedelta(days=7),
        end_date=now + timedelta(days=8),
        capacity=200,
        visibility="public",
        is_free=True,
        price=None,
        category_id=category_id,
        tag_ids=tag_ids or [],
    )


def test_create_event_with_category():
    """Creating an event with a valid category_id stores it on the entity."""
    cat = _make_category()
    entity = _create(
        FakeEventRepository(),
        cat_repo=FakeCategoryRepository([cat]),
        category_id=cat.id,
    )
    assert entity.category_id == cat.id


def test_create_event_invalid_category_raises():
    """Creating an event with a non-existent category_id raises CategoryNotFoundError."""
    with pytest.raises(CategoryNotFoundError):
        _create(
            FakeEventRepository(),
            cat_repo=FakeCategoryRepository(),
            category_id=uuid.uuid4(),
        )


def test_create_event_no_category():
    """Creating an event without a category stores category_id=None."""
    entity = _create(FakeEventRepository())
    assert entity.category_id is None


def test_create_event_with_tags():
    """Creating an event with tag_ids stores tag UUIDs on the entity."""
    t1, t2 = _make_tag("jazz"), _make_tag("outdoor")
    tag_repo = FakeTagRepository([t1, t2])
    entity = _create(
        FakeEventRepository(),
        tag_repo=tag_repo,
        tag_ids=[t1.id, t2.id],
    )
    assert set(entity.tag_ids) == {t1.id, t2.id}


def test_create_event_invalid_tag_raises():
    """Creating an event with a non-existent tag_id raises TagNotFoundError."""
    with pytest.raises(TagNotFoundError):
        _create(
            FakeEventRepository(),
            tag_repo=FakeTagRepository(),
            tag_ids=[uuid.uuid4()],
        )


def test_update_event_sets_category():
    """Patching category_id via UpdateEventUseCase updates the field."""
    cat = _make_category()
    cat_repo = FakeCategoryRepository([cat])
    event = make_event(category_id=None)
    event_repo = FakeEventRepository([event])
    UpdateEventUseCase(event_repo, category_repo=cat_repo).execute(
        event_id=event.id,
        organiser_id=event.organiser_id,
        category_id=cat.id,
    )
    updated = event_repo.get_by_id(event.id)
    assert updated.category_id == cat.id


def test_update_event_sets_tags():
    """Patching tag_ids via UpdateEventUseCase replaces the tag list."""
    t1, t2 = _make_tag("rock"), _make_tag("pop")
    tag_repo = FakeTagRepository([t1, t2])
    event = make_event(tag_ids=[])
    event_repo = FakeEventRepository([event])
    UpdateEventUseCase(event_repo, tag_repo=tag_repo).execute(
        event_id=event.id,
        organiser_id=event.organiser_id,
        tag_ids=[t1.id, t2.id],
    )
    updated = event_repo.get_by_id(event.id)
    assert set(updated.tag_ids) == {t1.id, t2.id}
