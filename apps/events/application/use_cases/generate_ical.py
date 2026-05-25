"""Use case: generate an iCalendar (.ics) file for an event."""

from __future__ import annotations

import uuid

from icalendar import Calendar, Event

from apps.events.domain.repositories import IEventRepository


class GenerateIcalUseCase:
    """Build a standards-compliant iCalendar file for a single event."""

    def __init__(self, event_repo: IEventRepository) -> None:
        self._events = event_repo

    def execute(self, *, event_id: uuid.UUID) -> bytes:
        """Load the event and return the .ics content as bytes."""
        entity = self._events.get_by_id(event_id)

        cal = Calendar()
        cal.add("prodid", "-//Sansaar//Event Universe//EN")
        cal.add("version", "2.0")

        vevent = Event()
        vevent.add("uid", f"{entity.id}@sansaar.com")
        vevent.add("summary", entity.title)
        vevent.add("description", entity.description)
        vevent.add("location", entity.location)
        vevent.add("dtstart", entity.start_date)
        vevent.add("dtend", entity.end_date)
        vevent.add("dtstamp", entity.created_at)

        cal.add_component(vevent)
        return cal.to_ical()
