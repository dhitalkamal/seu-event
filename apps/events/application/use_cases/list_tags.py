"""Use case: list all tags."""

from __future__ import annotations

from apps.events.domain.entities import TagEntity
from apps.events.domain.repositories import ITagRepository


class ListTagsUseCase:
    """Return every tag in the system."""

    def __init__(self, tag_repo: ITagRepository) -> None:
        self._tags = tag_repo

    def execute(self) -> list[TagEntity]:
        """Return all tags, unfiltered."""
        return self._tags.list_all()
