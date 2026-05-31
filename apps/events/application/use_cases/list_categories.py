"""Use case: list all event categories."""

from __future__ import annotations

from apps.events.domain.entities import CategoryEntity
from apps.events.domain.repositories import ICategoryRepository


class ListCategoriesUseCase:
    """Return every category in the system."""

    def __init__(self, category_repo: ICategoryRepository) -> None:
        self._categories = category_repo

    def execute(self) -> list[CategoryEntity]:
        """Return all categories, unfiltered."""
        return self._categories.list_all()
