"""Use case: create a new event category."""

from __future__ import annotations

import uuid

from apps.events.domain.entities import CategoryEntity
from apps.events.domain.exceptions import CategoryDepthExceededError
from apps.events.domain.repositories import ICategoryRepository

# ! categories are limited to 3 levels: root (0), child (1), grandchild (2)
_MAX_DEPTH = 2


class CreateCategoryUseCase:
    """Persist a new category, enforcing the 3-level depth limit."""

    def __init__(self, category_repo: ICategoryRepository) -> None:
        self._categories = category_repo

    def execute(
        self,
        *,
        name: str,
        slug: str,
        parent_id: uuid.UUID | None,
    ) -> CategoryEntity:
        """
        Validate depth, then create the category.

        @param name - display name of the category
        @param slug - URL-safe identifier, unique by convention
        @param parent_id - UUID of parent category; None for root
        @raises CategoryNotFoundError if parent_id does not exist
        @raises CategoryDepthExceededError if parent is already at max depth
        """
        depth = 0
        if parent_id is not None:
            parent = self._categories.get_by_id(parent_id)
            depth = parent.depth + 1
            if depth > _MAX_DEPTH:
                raise CategoryDepthExceededError(f"Categories may not exceed depth {_MAX_DEPTH}.")

        entity = CategoryEntity(
            id=uuid.uuid4(),
            name=name,
            slug=slug,
            parent_id=parent_id,
            depth=depth,
        )
        return self._categories.create(entity)
