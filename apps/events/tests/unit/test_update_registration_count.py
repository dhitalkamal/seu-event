"""Unit tests for UpdateRegistrationCountUseCase."""

from __future__ import annotations

import uuid

import pytest

from apps.events.application.use_cases.update_registration_count import (
    UpdateRegistrationCountUseCase,
)
from apps.events.domain.exceptions import EventNotFoundError
from apps.events.tests.unit.fakes import FakeEventRepository, make_event


def test_increment_registered_count():
    """Incrementing by 1 increases registered_count by 1."""
    event = make_event(registered_count=5, status="published")
    repo = FakeEventRepository([event])
    UpdateRegistrationCountUseCase(repo).execute(event_id=event.id, delta=1)
    updated = repo.get_by_id(event.id)
    assert updated.registered_count == 6


def test_decrement_registered_count():
    """Decrementing by 1 decreases registered_count by 1."""
    event = make_event(registered_count=3, status="published")
    repo = FakeEventRepository([event])
    UpdateRegistrationCountUseCase(repo).execute(event_id=event.id, delta=-1)
    updated = repo.get_by_id(event.id)
    assert updated.registered_count == 2


def test_count_does_not_go_below_zero():
    """registered_count is clamped at 0 -- never goes negative."""
    event = make_event(registered_count=0, status="published")
    repo = FakeEventRepository([event])
    UpdateRegistrationCountUseCase(repo).execute(event_id=event.id, delta=-1)
    updated = repo.get_by_id(event.id)
    assert updated.registered_count == 0


def test_missing_event_raises():
    """EventNotFoundError raised when event does not exist."""
    repo = FakeEventRepository()
    with pytest.raises(EventNotFoundError):
        UpdateRegistrationCountUseCase(repo).execute(event_id=uuid.uuid4(), delta=1)
