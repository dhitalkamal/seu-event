"""Unit tests for CompleteEventUseCase."""

from __future__ import annotations

import uuid

import pytest

from apps.events.application.use_cases.complete_event import CompleteEventUseCase
from apps.events.domain.exceptions import EventNotOwnedError, InvalidEventStatusTransitionError
from apps.events.tests.unit.fakes import FakeEventRepository, make_event


def _uc(events=None) -> CompleteEventUseCase:
    return CompleteEventUseCase(FakeEventRepository(events or []))


def test_complete_event_sets_status_completed():
    """Completing a published event sets status to completed."""
    organiser_id = uuid.uuid4()
    event = make_event(organiser_id=organiser_id, status="published")
    result = _uc(events=[event]).execute(event_id=event.id, organiser_id=organiser_id)
    assert result.status == "completed"


def test_complete_event_wrong_owner_raises():
    """Completing an event you do not own raises EventNotOwnedError."""
    event = make_event(organiser_id=uuid.uuid4(), status="published")
    with pytest.raises(EventNotOwnedError):
        _uc(events=[event]).execute(event_id=event.id, organiser_id=uuid.uuid4())


def test_complete_event_non_published_raises():
    """Completing a draft event raises InvalidEventStatusTransitionError."""
    organiser_id = uuid.uuid4()
    event = make_event(organiser_id=organiser_id, status="draft")
    with pytest.raises(InvalidEventStatusTransitionError):
        _uc(events=[event]).execute(event_id=event.id, organiser_id=organiser_id)
