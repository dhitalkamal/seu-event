"""Use case: create a new tag."""

from __future__ import annotations

import uuid

from apps.events.domain.entities import TagEntity
from apps.events.domain.exceptions import TagAlreadyExistsError
from apps.events.domain.repositories import ITagRepository


class CreateTagUseCase:
    """Persist a new tag, enforcing slug uniqueness."""

    def __init__(self, tag_repo: ITagRepository) -> None:
        self._tags = tag_repo

    def execute(self, *, name: str, slug: str) -> TagEntity:
        """
        Check slug uniqueness then create the tag.

        @param name - display name
        @param slug - URL-safe unique identifier
        @raises TagAlreadyExistsError if slug is already taken
        """
        if self._tags.get_by_slug(slug) is not None:
            raise TagAlreadyExistsError(f"A tag with slug '{slug}' already exists.")

        entity = TagEntity(id=uuid.uuid4(), name=name, slug=slug, usage_count=0)
        return self._tags.create(entity)
