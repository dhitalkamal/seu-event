"""Unit tests for hybrid event mode and virtual capacity."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from apps.events.tests.unit.fakes import FakeEventRepository, make_event


def test_event_entity_has_event_mode_field():
    """EventEntity has an event_mode field defaulting to physical."""
    event = make_event()
    assert hasattr(event, "event_mode")
    assert event.event_mode == "physical"


def test_event_entity_has_virtual_capacity_field():
    """EventEntity has a virtual_capacity field that can be None."""
    event = make_event()
    assert hasattr(event, "virtual_capacity")
    assert event.virtual_capacity is None


def test_physical_event_is_at_capacity_uses_registered_count():
    """Physical events check capacity the standard way."""
    event = make_event(capacity=10, registered_count=10, event_mode="physical")
    assert event.is_at_capacity is True


def test_virtual_event_is_at_capacity_uses_registered_count():
    """Virtual events check capacity the standard way (virtual_capacity is None)."""
    event = make_event(capacity=10, registered_count=10, event_mode="virtual")
    assert event.is_at_capacity is True


def test_hybrid_event_not_at_capacity_when_virtual_spots_remain():
    """Hybrid event is not at capacity when virtual_capacity has remaining spots."""
    # physical full, but virtual still open
    event = make_event(
        capacity=5,
        registered_count=7,
        event_mode="hybrid",
        virtual_capacity=10,
    )
    # total effective = physical(5) + virtual(10) = 15; 7 < 15
    assert event.is_at_capacity is False


def test_hybrid_event_at_capacity_when_all_spots_taken():
    """Hybrid event is at capacity when both physical and virtual are full."""
    event = make_event(
        capacity=5,
        registered_count=15,
        event_mode="hybrid",
        virtual_capacity=10,
    )
    # total = 5 + 10 = 15; 15 >= 15
    assert event.is_at_capacity is True


def test_hybrid_event_without_virtual_capacity_behaves_like_physical():
    """Hybrid event with no virtual_capacity falls back to physical capacity only."""
    event = make_event(
        capacity=10,
        registered_count=10,
        event_mode="hybrid",
        virtual_capacity=None,
    )
    assert event.is_at_capacity is True


def test_create_event_with_hybrid_mode():
    """CreateEventUseCase accepts event_mode='hybrid' and virtual_capacity."""
    from apps.events.application.use_cases.create_event import CreateEventUseCase
    from apps.events.tests.unit.fakes import FakeCategoryRepository, FakeTagRepository

    repo = FakeEventRepository()
    now = datetime.now(timezone.utc)
    result = CreateEventUseCase(
        repo,
        category_repo=FakeCategoryRepository(),
        tag_repo=FakeTagRepository(),
    ).execute(
        organiser_id=uuid.uuid4(),
        title="Hybrid Conference",
        description="Both in-person and online.",
        location="Kathmandu",
        start_date=now + timedelta(days=7),
        end_date=now + timedelta(days=8),
        capacity=100,
        visibility="public",
        is_free=True,
        event_mode="hybrid",
        virtual_capacity=200,
    )
    assert result.event_mode == "hybrid"
    assert result.virtual_capacity == 200
