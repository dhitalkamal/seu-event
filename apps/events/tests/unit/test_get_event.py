"""Unit tests for GetEventUseCase."""

from __future__ import annotations

import uuid

import pytest

from apps.events.application.use_cases.get_event import GetEventUseCase
from apps.events.domain.exceptions import EventNotFoundError
from apps.events.tests.unit.fakes import FakeEventRepository, make_event


def test_get_event_returns_entity():
    """Fetching an existing event returns the correct entity."""
    event = make_event(title="My Event")
    repo = FakeEventRepository([event])
    result = GetEventUseCase(repo).execute(event_id=event.id)
    assert result.id == event.id
    assert result.title == "My Event"


def test_get_event_missing_raises():
    """Fetching a non-existent event raises EventNotFoundError."""
    repo = FakeEventRepository()
    with pytest.raises(EventNotFoundError):
        GetEventUseCase(repo).execute(event_id=uuid.uuid4())
