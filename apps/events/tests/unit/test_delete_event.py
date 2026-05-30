"""Unit tests for DeleteEventUseCase."""

from __future__ import annotations

import uuid

import pytest

from apps.events.application.use_cases.delete_event import DeleteEventUseCase
from apps.events.domain.exceptions import EventNotFoundError, EventNotOwnedError
from apps.events.tests.unit.fakes import FakeEventRepository, make_event


def test_delete_event_sets_deleted_at_and_cancelled():
    """Soft-deleting an event sets deleted_at and status to cancelled."""
    organizer_id = uuid.uuid4()
    event = make_event(organizer_id=organizer_id, status="draft")
    repo = FakeEventRepository([event])
    DeleteEventUseCase(repo).execute(event_id=event.id, organizer_id=organizer_id)
    stored = repo._store[event.id]
    assert stored.deleted_at is not None
    assert stored.status == "cancelled"


def test_delete_event_wrong_owner_raises():
    """Deleting an event you do not own raises EventNotOwnedError."""
    event = make_event(organizer_id=uuid.uuid4())
    repo = FakeEventRepository([event])
    with pytest.raises(EventNotOwnedError):
        DeleteEventUseCase(repo).execute(event_id=event.id, organizer_id=uuid.uuid4())


def test_delete_event_not_retrievable_after_delete():
    """A soft-deleted event raises EventNotFoundError on subsequent get_by_id."""
    organizer_id = uuid.uuid4()
    event = make_event(organizer_id=organizer_id)
    repo = FakeEventRepository([event])
    DeleteEventUseCase(repo).execute(event_id=event.id, organizer_id=organizer_id)
    with pytest.raises(EventNotFoundError):
        repo.get_by_id(event.id)
