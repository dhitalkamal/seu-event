"""Abstract repository interfaces for the events module. Implemented in the infrastructure layer."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.events.domain.entities import EventEntity


class IEventRepository(ABC):
    """Persistence contract for Event aggregates."""

    @abstractmethod
    def create(self, entity: EventEntity) -> EventEntity: ...

    @abstractmethod
    def get_by_id(self, event_id: uuid.UUID) -> EventEntity: ...

    @abstractmethod
    def update(self, entity: EventEntity) -> EventEntity: ...
