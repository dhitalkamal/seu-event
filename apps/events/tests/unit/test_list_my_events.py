"""Unit tests for ListMyEventsUseCase."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from apps.events.application.use_cases.list_my_events import ListMyEventsUseCase
from apps.events.tests.unit.fakes import FakeEventRepository, make_event


def test_list_my_events_returns_all_statuses():
    """Returns own events at all statuses: draft, published, cancelled."""
    organizer_id = uuid.uuid4()
    draft = make_event(organizer_id=organizer_id, status="draft")
    published = make_event(organizer_id=organizer_id, status="published")
    cancelled = make_event(organizer_id=organizer_id, status="cancelled")
    repo = FakeEventRepository([draft, published, cancelled])
    results = ListMyEventsUseCase(repo).execute(organizer_id=organizer_id)
    assert len(results) == 3


def test_list_my_events_excludes_soft_deleted():
    """Soft-deleted events are not returned."""
    organizer_id = uuid.uuid4()
    deleted = make_event(organizer_id=organizer_id, deleted_at=datetime.now(timezone.utc))
    active = make_event(organizer_id=organizer_id)
    repo = FakeEventRepository([deleted, active])
    results = ListMyEventsUseCase(repo).execute(organizer_id=organizer_id)
    assert len(results) == 1
    assert results[0].id == active.id


def test_list_my_events_excludes_other_organizers():
    """Events from other organizers are not included."""
    organizer_id = uuid.uuid4()
    own = make_event(organizer_id=organizer_id)
    other = make_event(organizer_id=uuid.uuid4())
    repo = FakeEventRepository([own, other])
    results = ListMyEventsUseCase(repo).execute(organizer_id=organizer_id)
    assert len(results) == 1
    assert results[0].id == own.id


def test_list_my_events_empty_when_none():
    """Returns empty list when the organizer has no events."""
    repo = FakeEventRepository()
    results = ListMyEventsUseCase(repo).execute(organizer_id=uuid.uuid4())
    assert results == []
