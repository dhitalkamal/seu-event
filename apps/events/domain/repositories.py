"""Abstract repository interfaces for the events module. Implemented in the infrastructure layer."""

from __future__ import annotations

from abc import ABC, abstractmethod

from apps.events.domain.entities import EventEntity


class IEventRepository(ABC):
    """Persistence contract for Event aggregates."""

    @abstractmethod
    def create(self, entity: EventEntity) -> EventEntity: ...
