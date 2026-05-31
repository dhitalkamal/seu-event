"""Pure Python domain entities for the events module with no framework dependencies."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass(slots=True)
class TagEntity:
    """A free-form label that can be attached to events."""

    id: uuid.UUID
    name: str
    slug: str
    usage_count: int = 0


@dataclass(slots=True)
class CategoryEntity:
    """A hierarchical event category. Maximum 3 levels deep (depth 0, 1, 2)."""

    id: uuid.UUID
    name: str
    slug: str
    depth: int
    parent_id: uuid.UUID | None = None


@dataclass(slots=True)
class EventEntity:
    """A single event on the Sansaar platform."""

    id: uuid.UUID
    organizer_id: uuid.UUID
    title: str
    description: str
    location: str
    start_date: datetime
    end_date: datetime
    capacity: int
    registered_count: int
    status: str
    visibility: str
    is_free: bool
    price: Decimal
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    cover_image: str | None = None
    is_online: bool = False
    online_url: str | None = None
    category_id: uuid.UUID | None = None
    tag_ids: list[uuid.UUID] = field(default_factory=list)
    # ! primary USP - empty list means no restriction (visible to everyone)
    allowed_domains: list[str] = field(default_factory=list)
    # set on events generated as part of a recurrence series
    parent_event_id: uuid.UUID | None = None
    # optional: set when the event belongs to an organization rather than an individual
    organization_id: uuid.UUID | None = None
    # venue reference and coordinates; lat/lng supplied by the client (client-side geocoding)
    venue_id: uuid.UUID | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    # ! event_mode replaces the boolean is_online; physical / virtual / hybrid
    event_mode: str = "physical"
    # extra capacity for hybrid events (online attendees); None means unlimited or not applicable
    virtual_capacity: int | None = None
    # overbooking allowance as a percentage (0 = no overbooking)
    overbooking_percent: int = 0
    # when true, users who register after capacity is full join a waitlist instead of being rejected
    waitlist_enabled: bool = True

    @property
    def is_at_capacity(self) -> bool:
        """True when no spots remain.

        For hybrid events the effective capacity is physical + virtual.
        For all other modes it is just capacity.
        Overbooking percent is applied on top of the effective capacity.
        """
        if self.event_mode == "hybrid" and self.virtual_capacity is not None:
            effective = self.capacity + self.virtual_capacity
        else:
            effective = self.capacity
        effective_with_overbooking = effective * (1 + self.overbooking_percent / 100.0)
        return self.registered_count >= effective_with_overbooking
