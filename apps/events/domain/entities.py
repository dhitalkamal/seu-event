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
    online_url: str | None = None
    category_id: uuid.UUID | None = None
    tag_ids: list[uuid.UUID] = field(default_factory=list)
    # ! primary USP - empty list means no restriction (visible to everyone)
    allowed_domains: list[str] = field(default_factory=list)

    @property
    def is_at_capacity(self) -> bool:
        """True when no spots remain."""
        return self.registered_count >= self.capacity
