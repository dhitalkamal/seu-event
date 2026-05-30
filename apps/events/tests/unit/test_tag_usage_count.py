"""Unit tests for tag usage_count increment on event create and update."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from apps.events.application.use_cases.create_event import CreateEventUseCase
from apps.events.application.use_cases.update_event import UpdateEventUseCase
from apps.events.domain.entities import TagEntity
from apps.events.tests.unit.fakes import (
    FakeCategoryRepository,
    FakeEventRepository,
    FakeTagRepository,
    make_event,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _make_tag(name: str) -> TagEntity:
    return TagEntity(id=uuid.uuid4(), name=name, slug=name.lower(), usage_count=0)


def test_create_event_increments_tag_usage_count():
    """Assigning tags at create time increments each tag's usage_count by 1."""
    t1, t2 = _make_tag("rock"), _make_tag("live")
    tag_repo = FakeTagRepository([t1, t2])
    now = _now()
    CreateEventUseCase(
        FakeEventRepository(),
        category_repo=FakeCategoryRepository(),
        tag_repo=tag_repo,
    ).execute(
        organizer_id=uuid.uuid4(),
        title="Rock Night",
        description="Live rock music.",
        location="Kathmandu",
        start_date=now + timedelta(days=7),
        end_date=now + timedelta(days=8),
        capacity=100,
        visibility="public",
        is_free=True,
        price=None,
        category_id=None,
        tag_ids=[t1.id, t2.id],
    )
    assert tag_repo.get_by_id(t1.id).usage_count == 1
    assert tag_repo.get_by_id(t2.id).usage_count == 1


def test_update_event_increments_tag_usage_count():
    """Replacing tags via update increments usage_count for each newly assigned tag."""
    t1, t2 = _make_tag("jazz"), _make_tag("outdoor")
    tag_repo = FakeTagRepository([t1, t2])
    event = make_event(tag_ids=[])
    event_repo = FakeEventRepository([event])
    UpdateEventUseCase(event_repo, tag_repo=tag_repo).execute(
        event_id=event.id,
        organizer_id=event.organizer_id,
        tag_ids=[t1.id, t2.id],
    )
    assert tag_repo.get_by_id(t1.id).usage_count == 1
    assert tag_repo.get_by_id(t2.id).usage_count == 1


def test_create_event_no_tags_no_increment():
    """Creating an event with no tags leaves usage_count untouched."""
    t1 = _make_tag("unused")
    tag_repo = FakeTagRepository([t1])
    now = _now()
    CreateEventUseCase(
        FakeEventRepository(),
        category_repo=FakeCategoryRepository(),
        tag_repo=tag_repo,
    ).execute(
        organizer_id=uuid.uuid4(),
        title="Solo Event",
        description="No tags.",
        location="Pokhara",
        start_date=now + timedelta(days=7),
        end_date=now + timedelta(days=8),
        capacity=50,
        visibility="public",
        is_free=True,
        price=None,
        category_id=None,
        tag_ids=[],
    )
    assert tag_repo.get_by_id(t1.id).usage_count == 0
