"""Unit tests for ListEventsUseCase."""

from __future__ import annotations

import uuid

from apps.events.application.use_cases.list_events import ListEventsUseCase
from apps.events.tests.unit.fakes import FakeEventRepository, make_event


def test_list_events_returns_published_public_only():
    """Only PUBLISHED and PUBLIC events are returned."""
    draft = make_event(status="draft", visibility="public")
    private = make_event(status="published", visibility="private")
    public = make_event(status="published", visibility="public")
    repo = FakeEventRepository([draft, private, public])
    results = ListEventsUseCase(repo).execute()
    assert len(results) == 1
    assert results[0].id == public.id


def test_list_events_filter_by_organizer_id():
    """Filtering by organizer_id returns only that organizer's events."""
    organizer_id = uuid.uuid4()
    own = make_event(status="published", visibility="public", organizer_id=organizer_id)
    other = make_event(status="published", visibility="public")
    repo = FakeEventRepository([own, other])
    results = ListEventsUseCase(repo).execute(organizer_id=organizer_id)
    assert len(results) == 1
    assert results[0].id == own.id


def test_list_events_filter_by_is_free():
    """Filtering by is_free returns only matching events."""
    free = make_event(status="published", visibility="public", is_free=True)
    paid = make_event(status="published", visibility="public", is_free=False)
    repo = FakeEventRepository([free, paid])
    results = ListEventsUseCase(repo).execute(is_free=True)
    assert len(results) == 1
    assert results[0].id == free.id


def test_list_events_search_by_title():
    """Search filters by case-insensitive title contains."""
    match = make_event(status="published", visibility="public", title="Sansaar Conference")
    no_match = make_event(status="published", visibility="public", title="Other Event")
    repo = FakeEventRepository([match, no_match])
    results = ListEventsUseCase(repo).execute(search="sansaar")
    assert len(results) == 1
    assert results[0].id == match.id


def test_list_events_returns_empty_when_no_matches():
    """Returns an empty list when there are no published public events."""
    repo = FakeEventRepository()
    results = ListEventsUseCase(repo).execute()
    assert results == []


def test_list_events_filter_by_tag_id():
    """Filtering by tag_id returns only events that include the given tag."""
    from datetime import datetime, timedelta, timezone

    tag_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    with_tag = make_event(
        status="published",
        visibility="public",
        tag_ids=[tag_id],
        start_date=now + timedelta(days=1),
        end_date=now + timedelta(days=2),
    )
    without_tag = make_event(
        status="published",
        visibility="public",
        start_date=now + timedelta(days=1),
        end_date=now + timedelta(days=2),
    )
    repo = FakeEventRepository([with_tag, without_tag])
    results = ListEventsUseCase(repo).execute(tag_id=tag_id)
    assert len(results) == 1
    assert results[0].id == with_tag.id


def test_list_events_filter_by_date_from():
    """Filtering by date_from excludes events that start before the given date."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    future = make_event(
        status="published",
        visibility="public",
        start_date=now + timedelta(days=10),
        end_date=now + timedelta(days=11),
    )
    past = make_event(
        status="published",
        visibility="public",
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=1),
    )
    repo = FakeEventRepository([future, past])
    results = ListEventsUseCase(repo).execute(date_from=now + timedelta(days=5))
    assert len(results) == 1
    assert results[0].id == future.id


def test_list_events_filter_by_location():
    """Filtering by location returns only events with matching location."""
    kathmandu = make_event(status="published", visibility="public", location="Kathmandu, Nepal")
    pokhara = make_event(status="published", visibility="public", location="Pokhara, Nepal")
    repo = FakeEventRepository([kathmandu, pokhara])
    results = ListEventsUseCase(repo).execute(location="kathmandu")
    assert len(results) == 1
    assert results[0].id == kathmandu.id
