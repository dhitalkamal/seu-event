"""Unit tests for UpdateEventUseCase."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from apps.events.application.use_cases.update_event import UpdateEventUseCase
from apps.events.domain.exceptions import EventDateError, EventNotOwnedError
from apps.events.tests.unit.fakes import FakeEventRepository, make_event


def _future(days: int = 7) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


def test_update_event_applies_provided_fields():
    """Provided fields are updated on the returned entity."""
    organiser_id = uuid.uuid4()
    event = make_event(organiser_id=organiser_id, title="Old Title", capacity=50)
    repo = FakeEventRepository([event])
    result = UpdateEventUseCase(repo).execute(
        event_id=event.id,
        organiser_id=organiser_id,
        title="New Title",
        capacity=200,
    )
    assert result.title == "New Title"
    assert result.capacity == 200


def test_update_event_skips_unprovided_fields():
    """Fields not included in the call are left unchanged."""
    organiser_id = uuid.uuid4()
    event = make_event(organiser_id=organiser_id, title="Keep Me", description="Keep too")
    repo = FakeEventRepository([event])
    result = UpdateEventUseCase(repo).execute(
        event_id=event.id,
        organiser_id=organiser_id,
        title="Changed",
    )
    assert result.description == "Keep too"


def test_update_event_wrong_owner_raises():
    """Updating an event you do not own raises EventNotOwnedError."""
    event = make_event(organiser_id=uuid.uuid4())
    repo = FakeEventRepository([event])
    with pytest.raises(EventNotOwnedError):
        UpdateEventUseCase(repo).execute(
            event_id=event.id,
            organiser_id=uuid.uuid4(),
            title="Hack",
        )


def test_update_event_date_change_revalidates():
    """Changing end_date to before start_date raises EventDateError."""
    organiser_id = uuid.uuid4()
    event = make_event(
        organiser_id=organiser_id,
        start_date=_future(7),
        end_date=_future(8),
    )
    repo = FakeEventRepository([event])
    with pytest.raises(EventDateError):
        UpdateEventUseCase(repo).execute(
            event_id=event.id,
            organiser_id=organiser_id,
            end_date=_future(6),
        )
