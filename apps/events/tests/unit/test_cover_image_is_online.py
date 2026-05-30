"""Unit tests for cover_image and is_online fields on EventEntity and create/update use cases."""

from __future__ import annotations

from apps.events.application.use_cases.create_event import CreateEventUseCase
from apps.events.application.use_cases.update_event import UpdateEventUseCase
from apps.events.tests.unit.fakes import FakeEventRepository, make_event


def test_event_defaults_is_online_false():
    """EventEntity.is_online defaults to False when not supplied."""
    event = make_event()
    assert event.is_online is False


def test_event_defaults_cover_image_none():
    """EventEntity.cover_image defaults to None when not supplied."""
    event = make_event()
    assert event.cover_image is None


def test_create_event_stores_is_online():
    """Creating an event with is_online=True persists the flag."""
    repo = FakeEventRepository()
    import uuid
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    entity = CreateEventUseCase(repo).execute(
        organizer_id=uuid.uuid4(),
        title="Online Conf",
        description="Fully remote conference.",
        location="Virtual",
        start_date=now + timedelta(days=7),
        end_date=now + timedelta(days=8),
        capacity=500,
        visibility="public",
        is_free=True,
        price=None,
        is_online=True,
        cover_image=None,
    )
    assert entity.is_online is True


def test_create_event_stores_cover_image():
    """Creating an event with a cover_image URL persists it."""
    repo = FakeEventRepository()
    import uuid
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    url = "https://example.com/cover.jpg"
    entity = CreateEventUseCase(repo).execute(
        organizer_id=uuid.uuid4(),
        title="Art Show",
        description="Annual art exhibition.",
        location="Gallery 9",
        start_date=now + timedelta(days=7),
        end_date=now + timedelta(days=8),
        capacity=200,
        visibility="public",
        is_free=False,
        price=None,
        is_online=False,
        cover_image=url,
    )
    assert entity.cover_image == url


def test_update_event_sets_is_online():
    """Patching is_online via UpdateEventUseCase updates the field."""
    event = make_event(is_online=False)
    repo = FakeEventRepository([event])
    UpdateEventUseCase(repo).execute(
        event_id=event.id,
        organizer_id=event.organizer_id,
        is_online=True,
    )
    updated = repo.get_by_id(event.id)
    assert updated.is_online is True


def test_update_event_sets_cover_image():
    """Patching cover_image via UpdateEventUseCase updates the field."""
    event = make_event(cover_image=None)
    repo = FakeEventRepository([event])
    url = "https://example.com/new-cover.png"
    UpdateEventUseCase(repo).execute(
        event_id=event.id,
        organizer_id=event.organizer_id,
        cover_image=url,
    )
    updated = repo.get_by_id(event.id)
    assert updated.cover_image == url
