"""Unit tests for PublishEventUseCase."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from apps.events.application.use_cases.publish_event import PublishEventUseCase
from apps.events.domain.exceptions import (
    EventDateError,
    EventNotOwnedError,
    InvalidEventStatusTransitionError,
)
from apps.events.tests.unit.fakes import FakeEventRepository, make_event


def _future(days: int = 7) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


def test_publish_event_sets_status_published():
    """Publishing a draft event with a future start_date sets status to published."""
    organiser_id = uuid.uuid4()
    event = make_event(organiser_id=organiser_id, status="draft", start_date=_future(7))
    repo = FakeEventRepository([event])
    result = PublishEventUseCase(repo).execute(event_id=event.id, organiser_id=organiser_id)
    assert result.status == "published"


def test_publish_event_wrong_owner_raises():
    """Publishing an event you do not own raises EventNotOwnedError."""
    event = make_event(organiser_id=uuid.uuid4(), status="draft")
    repo = FakeEventRepository([event])
    with pytest.raises(EventNotOwnedError):
        PublishEventUseCase(repo).execute(event_id=event.id, organiser_id=uuid.uuid4())


def test_publish_event_non_draft_raises():
    """Publishing an already-published event raises InvalidEventStatusTransitionError."""
    organiser_id = uuid.uuid4()
    event = make_event(organiser_id=organiser_id, status="published")
    repo = FakeEventRepository([event])
    with pytest.raises(InvalidEventStatusTransitionError):
        PublishEventUseCase(repo).execute(event_id=event.id, organiser_id=organiser_id)


def test_publish_event_past_start_date_raises():
    """Publishing an event whose start_date has already passed raises EventDateError."""
    organiser_id = uuid.uuid4()
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    event = make_event(organiser_id=organiser_id, status="draft", start_date=past)
    repo = FakeEventRepository([event])
    with pytest.raises(EventDateError):
        PublishEventUseCase(repo).execute(event_id=event.id, organiser_id=organiser_id)
