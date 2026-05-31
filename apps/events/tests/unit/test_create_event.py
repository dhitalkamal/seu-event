"""Unit tests for event creation -- no database, hand-rolled fakes."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from apps.events.application.use_cases.create_event import CreateEventUseCase
from apps.events.domain.exceptions import EventDateError
from apps.events.tests.unit.fakes import FakeEventRepository


def _future(days: int = 7) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


def _uc(repo: FakeEventRepository | None = None) -> CreateEventUseCase:
    return CreateEventUseCase(repo or FakeEventRepository())


def _defaults(**overrides: object) -> dict:
    base: dict = {
        "organizer_id": uuid.uuid4(),
        "title": "Sansaar Conference",
        "description": "Annual tech conference.",
        "location": "Kathmandu",
        "start_date": _future(7),
        "end_date": _future(8),
        "capacity": 200,
        "visibility": "public",
        "is_free": True,
        "price": Decimal("0.00"),
    }
    base.update(overrides)
    return base


def test_create_event_returns_entity_with_correct_fields():
    """Returned entity reflects all submitted input fields."""
    entity = _uc().execute(**_defaults())
    assert entity.title == "Sansaar Conference"
    assert entity.description == "Annual tech conference."
    assert entity.location == "Kathmandu"
    assert entity.capacity == 200
    assert entity.visibility == "public"


def test_create_event_status_is_draft():
    """Status is always DRAFT on creation regardless of any other input."""
    entity = _uc().execute(**_defaults())
    assert entity.status == "draft"


def test_create_event_registered_count_is_zero():
    """No one is registered at creation time."""
    entity = _uc().execute(**_defaults())
    assert entity.registered_count == 0


def test_create_event_end_before_start_raises():
    """end_date before start_date raises EventDateError."""
    with pytest.raises(EventDateError):
        _uc().execute(**_defaults(start_date=_future(8), end_date=_future(7)))


def test_create_event_end_equals_start_raises():
    """end_date equal to start_date raises EventDateError."""
    t = _future(7)
    with pytest.raises(EventDateError):
        _uc().execute(**_defaults(start_date=t, end_date=t))


def test_create_event_free_event_price_zero():
    """Free events always have price forced to 0.00, even if a non-zero price is passed."""
    entity = _uc().execute(**_defaults(is_free=True, price=Decimal("100.00")))
    assert entity.price == Decimal("0.00")


def test_create_event_persists_in_repository():
    """The returned entity is actually stored and retrievable from the repo."""
    repo = FakeEventRepository()
    entity = _uc(repo).execute(**_defaults())
    assert entity.id in repo._store
