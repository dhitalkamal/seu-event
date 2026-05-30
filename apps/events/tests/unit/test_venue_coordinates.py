"""Unit tests for venue coordinates (latitude, longitude, venue_id) on EventEntity and CreateEvent."""

from __future__ import annotations

import uuid
from decimal import Decimal

from apps.events.application.use_cases.create_event import CreateEventUseCase
from apps.events.application.use_cases.update_event import UpdateEventUseCase
from apps.events.tests.unit.fakes import (
    FakeCategoryRepository,
    FakeEventRepository,
    FakeTagRepository,
    make_event,
)


class TestEventEntityVenueFields:
    """EventEntity carries optional latitude, longitude, and venue_id fields."""

    def test_event_entity_has_latitude_field(self) -> None:
        """latitude must be an optional Decimal on EventEntity."""
        event = make_event(latitude=Decimal("27.7172"))
        assert event.latitude == Decimal("27.7172")

    def test_event_entity_has_longitude_field(self) -> None:
        """longitude must be an optional Decimal on EventEntity."""
        event = make_event(longitude=Decimal("85.3240"))
        assert event.longitude == Decimal("85.3240")

    def test_event_entity_has_venue_id_field(self) -> None:
        """venue_id must be an optional UUID on EventEntity."""
        vid = uuid.uuid4()
        event = make_event(venue_id=vid)
        assert event.venue_id == vid

    def test_venue_fields_default_to_none(self) -> None:
        """latitude, longitude, and venue_id must default to None."""
        event = make_event()
        assert event.latitude is None
        assert event.longitude is None
        assert event.venue_id is None


class TestCreateEventWithVenueCoordinates:
    """CreateEventUseCase accepts and persists venue coordinate fields."""

    def test_create_event_stores_lat_lng(self) -> None:
        """lat/lng passed to create must appear on the returned entity."""
        repo = FakeEventRepository()
        organizer_id = uuid.uuid4()

        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        entity = CreateEventUseCase(
            repo,
            category_repo=FakeCategoryRepository(),
            tag_repo=FakeTagRepository(),
        ).execute(
            organizer_id=organizer_id,
            title="Geo Event",
            description="Has coordinates.",
            location="Patan, Nepal",
            start_date=now + timedelta(days=7),
            end_date=now + timedelta(days=8),
            capacity=50,
            visibility="public",
            is_free=True,
            latitude=Decimal("27.6588"),
            longitude=Decimal("85.3247"),
        )

        assert entity.latitude == Decimal("27.6588")
        assert entity.longitude == Decimal("85.3247")

    def test_create_event_stores_venue_id(self) -> None:
        """venue_id passed to create must appear on the returned entity."""
        repo = FakeEventRepository()
        organizer_id = uuid.uuid4()
        venue_id = uuid.uuid4()

        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        entity = CreateEventUseCase(
            repo,
            category_repo=FakeCategoryRepository(),
            tag_repo=FakeTagRepository(),
        ).execute(
            organizer_id=organizer_id,
            title="Venue Event",
            description="Has venue reference.",
            location="Lalitpur",
            start_date=now + timedelta(days=7),
            end_date=now + timedelta(days=8),
            capacity=50,
            visibility="public",
            is_free=True,
            venue_id=venue_id,
        )

        assert entity.venue_id == venue_id

    def test_create_event_without_venue_fields_has_none(self) -> None:
        """Omitting venue fields must result in None values on the entity."""
        repo = FakeEventRepository()
        organizer_id = uuid.uuid4()

        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        entity = CreateEventUseCase(
            repo,
            category_repo=FakeCategoryRepository(),
            tag_repo=FakeTagRepository(),
        ).execute(
            organizer_id=organizer_id,
            title="Plain Event",
            description="No coordinates.",
            location="Bhaktapur",
            start_date=now + timedelta(days=7),
            end_date=now + timedelta(days=8),
            capacity=50,
            visibility="public",
            is_free=True,
        )

        assert entity.latitude is None
        assert entity.longitude is None
        assert entity.venue_id is None


class TestUpdateEventWithVenueCoordinates:
    """UpdateEventUseCase allows patching venue coordinate fields."""

    def test_update_event_sets_lat_lng(self) -> None:
        """Patching lat/lng must update those fields on the stored entity."""
        event = make_event(latitude=None, longitude=None)
        repo = FakeEventRepository(events=[event])

        entity = UpdateEventUseCase(
            repo,
            category_repo=FakeCategoryRepository(),
            tag_repo=FakeTagRepository(),
        ).execute(
            event_id=event.id,
            organizer_id=event.organizer_id,
            latitude=Decimal("28.3949"),
            longitude=Decimal("84.1240"),
        )

        assert entity.latitude == Decimal("28.3949")
        assert entity.longitude == Decimal("84.1240")

    def test_update_event_sets_venue_id(self) -> None:
        """Patching venue_id must update that field on the stored entity."""
        event = make_event(venue_id=None)
        repo = FakeEventRepository(events=[event])
        new_venue_id = uuid.uuid4()

        entity = UpdateEventUseCase(
            repo,
            category_repo=FakeCategoryRepository(),
            tag_repo=FakeTagRepository(),
        ).execute(
            event_id=event.id,
            organizer_id=event.organizer_id,
            venue_id=new_venue_id,
        )

        assert entity.venue_id == new_venue_id
