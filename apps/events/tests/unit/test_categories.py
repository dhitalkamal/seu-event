"""Unit tests for Category domain entity and use cases."""

from __future__ import annotations

import uuid

import pytest

from apps.events.application.use_cases.create_category import CreateCategoryUseCase
from apps.events.application.use_cases.list_categories import ListCategoriesUseCase
from apps.events.domain.entities import CategoryEntity
from apps.events.domain.exceptions import CategoryDepthExceededError, CategoryNotFoundError
from apps.events.tests.unit.fakes import FakeCategoryRepository


def make_category(**kwargs: object) -> CategoryEntity:
    """Build a CategoryEntity with sensible defaults."""
    defaults: dict = {
        "id": uuid.uuid4(),
        "name": "Technology",
        "slug": "technology",
        "parent_id": None,
        "depth": 0,
    }
    defaults.update(kwargs)
    return CategoryEntity(**defaults)  # type: ignore[arg-type]


def test_create_root_category():
    """Creating a root category (no parent) sets depth=0."""
    repo = FakeCategoryRepository()
    entity = CreateCategoryUseCase(repo).execute(name="Music", slug="music", parent_id=None)
    assert entity.depth == 0
    assert entity.parent_id is None


def test_create_child_category():
    """Creating a child of a root category sets depth=1."""
    root = make_category(depth=0)
    repo = FakeCategoryRepository([root])
    child = CreateCategoryUseCase(repo).execute(name="Rock", slug="rock", parent_id=root.id)
    assert child.depth == 1
    assert child.parent_id == root.id


def test_create_grandchild_category():
    """Creating a grandchild (depth=2) is allowed."""
    root = make_category(depth=0)
    child = make_category(depth=1, parent_id=root.id)
    repo = FakeCategoryRepository([root, child])
    grandchild = CreateCategoryUseCase(repo).execute(
        name="Classic Rock", slug="classic-rock", parent_id=child.id
    )
    assert grandchild.depth == 2


def test_create_beyond_max_depth_raises():
    """Creating a category at depth=3 raises CategoryDepthExceededError."""
    root = make_category(depth=0)
    child = make_category(depth=1, parent_id=root.id)
    grandchild = make_category(depth=2, parent_id=child.id)
    repo = FakeCategoryRepository([root, child, grandchild])
    with pytest.raises(CategoryDepthExceededError):
        CreateCategoryUseCase(repo).execute(
            name="Too Deep", slug="too-deep", parent_id=grandchild.id
        )


def test_create_category_parent_not_found_raises():
    """Creating a category with a non-existent parent raises CategoryNotFoundError."""
    repo = FakeCategoryRepository()
    with pytest.raises(CategoryNotFoundError):
        CreateCategoryUseCase(repo).execute(name="Orphan", slug="orphan", parent_id=uuid.uuid4())


def test_list_categories_returns_all():
    """ListCategoriesUseCase returns every stored category."""
    cats = [make_category(name=f"Cat{i}", slug=f"cat-{i}") for i in range(3)]
    repo = FakeCategoryRepository(cats)
    result = ListCategoriesUseCase(repo).execute()
    assert len(result) == 3


def test_list_categories_empty():
    """ListCategoriesUseCase returns empty list when none exist."""
    repo = FakeCategoryRepository()
    assert ListCategoriesUseCase(repo).execute() == []
