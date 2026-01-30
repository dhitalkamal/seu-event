"""Unit tests for location-based event search and sort functionality."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from apps.events.tests.unit.fakes import FakeEventRepository, make_event


def _published(**kwargs: object):
    """Build a published public event with sensible defaults."""
    now = datetime.now(timezone.utc)
    defaults = {
        "status": "published",
        "visibility": "public",
        "start_date": now + timedelta(days=1),
        "end_date": now + timedelta(days=2),
    }
    defaults.update(kwargs)
    return make_event(**defaults)


def test_haversine_distance_known_pair():
    """haversine returns roughly 800 km between Kathmandu and Delhi."""
    from apps.events.infrastructure.haversine import haversine

    # Kathmandu: 27.7172, 85.3240 -- Delhi: 28.6139, 77.2090
    dist = haversine(27.7172, 85.3240, 28.6139, 77.2090)
    # actual is ~800 km; accept 750-850
    assert 750 < dist < 850


def test_haversine_same_point_is_zero():
    """haversine of identical coordinates is zero."""
    from apps.events.infrastructure.haversine import haversine

    assert haversine(27.7172, 85.3240, 27.7172, 85.3240) == 0.0


def test_list_events_filters_by_radius():
    """list_public returns only events within the given radius."""
    from apps.events.application.use_cases.list_events import ListEventsUseCase

    # Kathmandu lat/lng
    ktm_lat, ktm_lng = Decimal("27.7172"), Decimal("85.3240")
    # Pokhara: ~200 km from Kathmandu
    pkr_lat, pkr_lng = Decimal("28.2096"), Decimal("83.9856")
    # Delhi: ~1400 km from Kathmandu
    del_lat, del_lng = Decimal("28.6139"), Decimal("77.2090")

    event_near = _published(latitude=ktm_lat, longitude=ktm_lng)
    event_mid = _published(latitude=pkr_lat, longitude=pkr_lng)
    event_far = _published(latitude=del_lat, longitude=del_lng)
    event_no_coords = _published()  # no lat/lng, should be excluded when radius filter active

    repo = FakeEventRepository([event_near, event_mid, event_far, event_no_coords])
    results = ListEventsUseCase(repo).execute(
        lat=27.7172,
        lng=85.3240,
        radius_km=300.0,
    )
    ids = {e.id for e in results}
    assert event_near.id in ids
    assert event_mid.id in ids
    assert event_far.id not in ids
    assert event_no_coords.id not in ids


def test_list_events_no_radius_filter_returns_all():
    """list_public without lat/lng/radius returns all published events."""
    from apps.events.application.use_cases.list_events import ListEventsUseCase

    events = [_published() for _ in range(5)]
    repo = FakeEventRepository(events)
    results = ListEventsUseCase(repo).execute()
    assert len(results) == 5


def test_sort_by_distance_orders_closest_first():
    """sort_by=distance orders results from nearest to farthest."""
    from apps.events.application.use_cases.list_events import ListEventsUseCase

    ktm_lat, ktm_lng = Decimal("27.7172"), Decimal("85.3240")
    pkr_lat, pkr_lng = Decimal("28.2096"), Decimal("83.9856")

    event_far = _published(latitude=pkr_lat, longitude=pkr_lng)
    event_near = _published(latitude=ktm_lat, longitude=ktm_lng)

    repo = FakeEventRepository([event_far, event_near])
    results = ListEventsUseCase(repo).execute(
        lat=27.7172,
        lng=85.3240,
        sort_by="distance",
    )
    assert results[0].id == event_near.id
    assert results[1].id == event_far.id


def test_sort_by_popularity_orders_by_registered_count_desc():
    """sort_by=popularity orders by registered_count descending."""
    from apps.events.application.use_cases.list_events import ListEventsUseCase

    event_low = _published(registered_count=5)
    event_high = _published(registered_count=100)
    event_mid = _published(registered_count=50)

    repo = FakeEventRepository([event_low, event_high, event_mid])
    results = ListEventsUseCase(repo).execute(sort_by="popularity")
    assert results[0].id == event_high.id
    assert results[1].id == event_mid.id
    assert results[2].id == event_low.id


def test_sort_by_date_orders_by_start_date_asc():
    """sort_by=date orders by start_date ascending."""
    from apps.events.application.use_cases.list_events import ListEventsUseCase

    now = datetime.now(timezone.utc)
    event_later = _published(start_date=now + timedelta(days=10), end_date=now + timedelta(days=11))
    event_soon = _published(start_date=now + timedelta(days=2), end_date=now + timedelta(days=3))

    repo = FakeEventRepository([event_later, event_soon])
    results = ListEventsUseCase(repo).execute(sort_by="date")
    assert results[0].id == event_soon.id
    assert results[1].id == event_later.id
