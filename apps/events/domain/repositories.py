"""Abstract repository interfaces for the events module. Implemented in the infrastructure layer."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from apps.events.domain.entities import CategoryEntity, EventEntity


class ICategoryRepository(ABC):
    """Persistence contract for Category aggregates."""

    @abstractmethod
    def create(self, entity: CategoryEntity) -> CategoryEntity: ...

    @abstractmethod
    def get_by_id(self, category_id: uuid.UUID) -> CategoryEntity: ...

    @abstractmethod
    def list_all(self) -> list[CategoryEntity]: ...


class IEventRepository(ABC):
    """Persistence contract for Event aggregates."""

    @abstractmethod
    def create(self, entity: EventEntity) -> EventEntity: ...

    @abstractmethod
    def get_by_id(self, event_id: uuid.UUID) -> EventEntity: ...

    @abstractmethod
    def update(self, entity: EventEntity) -> EventEntity: ...

    @abstractmethod
    def list_public(
        self,
        *,
        organiser_id: uuid.UUID | None = None,
        is_free: bool | None = None,
        search: str | None = None,
    ) -> list[EventEntity]: ...

    @abstractmethod
    def list_by_organiser(self, organiser_id: uuid.UUID) -> list[EventEntity]: ...
