"""Unit tests for the seed_categories management command."""

from __future__ import annotations

from apps.events.application.use_cases.create_category import CreateCategoryUseCase
from apps.events.application.use_cases.list_categories import ListCategoriesUseCase
from apps.events.management.commands.seed_categories import SEED_CATEGORIES
from apps.events.tests.unit.fakes import FakeCategoryRepository


def test_seed_categories_constant_is_non_empty():
    """SEED_CATEGORIES must define at least one category to seed."""
    assert len(SEED_CATEGORIES) > 0


def test_seed_categories_entries_have_required_fields():
    """Every entry in SEED_CATEGORIES must have name and slug keys."""
    for entry in SEED_CATEGORIES:
        assert "name" in entry, f"missing 'name' in {entry}"
        assert "slug" in entry, f"missing 'slug' in {entry}"


def test_seed_creates_all_categories_in_repo():
    """Seeding via use case creates exactly len(SEED_CATEGORIES) root categories."""
    repo = FakeCategoryRepository()
    for entry in SEED_CATEGORIES:
        CreateCategoryUseCase(repo).execute(name=entry["name"], slug=entry["slug"], parent_id=None)
    result = ListCategoriesUseCase(repo).execute()
    assert len(result) == len(SEED_CATEGORIES)


def test_seed_categories_all_root_level():
    """All seeded categories are root-level (depth=0, no parent)."""
    repo = FakeCategoryRepository()
    for entry in SEED_CATEGORIES:
        CreateCategoryUseCase(repo).execute(name=entry["name"], slug=entry["slug"], parent_id=None)
    for cat in ListCategoriesUseCase(repo).execute():
        assert cat.depth == 0
        assert cat.parent_id is None


def test_seed_slugs_are_unique():
    """All slugs in SEED_CATEGORIES are unique, no accidental duplicates."""
    slugs = [e["slug"] for e in SEED_CATEGORIES]
    assert len(slugs) == len(set(slugs))
