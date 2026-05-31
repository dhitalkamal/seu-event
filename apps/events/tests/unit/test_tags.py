"""Unit tests for Tag domain entity and use cases."""

from __future__ import annotations

import uuid

import pytest

from apps.events.application.use_cases.create_tag import CreateTagUseCase
from apps.events.application.use_cases.list_tags import ListTagsUseCase
from apps.events.domain.exceptions import TagAlreadyExistsError
from apps.events.tests.unit.fakes import FakeTagRepository


def make_tag_via_repo(name: str, slug: str, usage_count: int = 0):
    """Helper: create a tag directly in a fresh repo and return (repo, entity)."""
    from apps.events.domain.entities import TagEntity

    repo = FakeTagRepository()
    entity = repo.create(TagEntity(id=uuid.uuid4(), name=name, slug=slug, usage_count=usage_count))
    return repo, entity


def test_create_tag_stores_name_and_slug():
    """Creating a tag persists name and slug with usage_count=0."""
    repo = FakeTagRepository()
    entity = CreateTagUseCase(repo).execute(name="Python", slug="python")
    assert entity.name == "Python"
    assert entity.slug == "python"
    assert entity.usage_count == 0


def test_create_tag_duplicate_slug_raises():
    """Creating two tags with the same slug raises TagAlreadyExistsError."""
    repo = FakeTagRepository()
    CreateTagUseCase(repo).execute(name="Python", slug="python")
    with pytest.raises(TagAlreadyExistsError):
        CreateTagUseCase(repo).execute(name="Python 2", slug="python")


def test_list_tags_returns_all():
    """ListTagsUseCase returns every stored tag."""
    repo = FakeTagRepository()
    for i in range(4):
        CreateTagUseCase(repo).execute(name=f"Tag{i}", slug=f"tag-{i}")
    result = ListTagsUseCase(repo).execute()
    assert len(result) == 4


def test_list_tags_empty():
    """ListTagsUseCase returns empty list when no tags exist."""
    repo = FakeTagRepository()
    assert ListTagsUseCase(repo).execute() == []
