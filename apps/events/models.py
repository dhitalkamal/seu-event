"""Re-export ORM models so Django's app registry finds them under the events label."""

from __future__ import annotations

from apps.events.infrastructure.models import Event

__all__ = ["Event"]
