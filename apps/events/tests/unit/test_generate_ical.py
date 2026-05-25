"""Tests for GenerateIcalUseCase."""

from __future__ import annotations

import uuid

import pytest

from apps.events.application.use_cases.generate_ical import GenerateIcalUseCase
from apps.events.domain.exceptions import EventNotFoundError
from apps.events.tests.unit.fakes import FakeEventRepository, make_event


class TestGenerateIcal:
    """Unit tests for GenerateIcalUseCase."""

    def test_returns_bytes(self) -> None:
        """Use case returns bytes (the .ics file content)."""
        event = make_event(status="published")
        repo = FakeEventRepository([event])
        result = GenerateIcalUseCase(repo).execute(event_id=event.id)
        assert isinstance(result, bytes)

    def test_content_starts_with_vcalendar(self) -> None:
        """iCal output begins with the VCALENDAR component."""
        event = make_event(status="published")
        repo = FakeEventRepository([event])
        result = GenerateIcalUseCase(repo).execute(event_id=event.id)
        assert result.startswith(b"BEGIN:VCALENDAR")

    def test_contains_event_title_as_summary(self) -> None:
        """SUMMARY field matches the event title."""
        event = make_event(title="My Test Event", status="published")
        repo = FakeEventRepository([event])
        result = GenerateIcalUseCase(repo).execute(event_id=event.id)
        assert b"My Test Event" in result

    def test_contains_uid_with_event_id(self) -> None:
        """UID field contains the event UUID."""
        event = make_event(status="published")
        repo = FakeEventRepository([event])
        result = GenerateIcalUseCase(repo).execute(event_id=event.id)
        assert str(event.id).encode() in result

    def test_contains_location(self) -> None:
        """LOCATION field contains the event location."""
        event = make_event(location="Kathmandu, Nepal", status="published")
        repo = FakeEventRepository([event])
        result = GenerateIcalUseCase(repo).execute(event_id=event.id)
        assert b"Kathmandu" in result

    def test_contains_dtstart_and_dtend(self) -> None:
        """Both DTSTART and DTEND are present."""
        event = make_event(status="published")
        repo = FakeEventRepository([event])
        result = GenerateIcalUseCase(repo).execute(event_id=event.id)
        assert b"DTSTART" in result
        assert b"DTEND" in result

    def test_raises_if_event_not_found(self) -> None:
        """EventNotFoundError is raised when event_id does not exist."""
        repo = FakeEventRepository()
        with pytest.raises(EventNotFoundError):
            GenerateIcalUseCase(repo).execute(event_id=uuid.uuid4())
