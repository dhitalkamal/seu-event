"""Pure Python domain entities for the events module with no framework dependencies."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(slots=True)
class EventEntity:
    """A single event on the Sansaar platform."""

    id: uuid.UUID
    organiser_id: uuid.UUID
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

    @property
    def is_at_capacity(self) -> bool:
        """True when no spots remain."""
        return self.registered_count >= self.capacity
