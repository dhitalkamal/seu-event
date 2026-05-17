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


def test_list_events_filter_by_organiser_id():
    """Filtering by organiser_id returns only that organiser's events."""
    organiser_id = uuid.uuid4()
    own = make_event(status="published", visibility="public", organiser_id=organiser_id)
    other = make_event(status="published", visibility="public")
    repo = FakeEventRepository([own, other])
    results = ListEventsUseCase(repo).execute(organiser_id=organiser_id)
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
