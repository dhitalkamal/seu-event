"""Management command to seed default event categories."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.events.application.use_cases.create_category import CreateCategoryUseCase
from apps.events.infrastructure.repositories import DjangoCategoryRepository

# * default categories to seed on a fresh install
SEED_CATEGORIES: list[dict[str, str]] = [
    {"name": "Conference", "slug": "conference"},
    {"name": "Workshop", "slug": "workshop"},
    {"name": "Gala", "slug": "gala"},
    {"name": "Lecture", "slug": "lecture"},
    {"name": "Symposium", "slug": "symposium"},
    {"name": "Summit", "slug": "summit"},
    {"name": "Networking", "slug": "networking"},
    {"name": "Hackathon", "slug": "hackathon"},
    {"name": "Career Fair", "slug": "career-fair"},
    {"name": "Cultural Show", "slug": "cultural-show"},
]


class Command(BaseCommand):
    """Seed the database with default event categories."""

    help = "Seed default event categories"

    def handle(self, *args: object, **options: object) -> None:
        """Create each category in SEED_CATEGORIES, skipping existing slugs."""
        repo = DjangoCategoryRepository()
        use_case = CreateCategoryUseCase(repo)
        existing_slugs = {c.slug for c in repo.list_all()}
        created = 0
        skipped = 0

        for entry in SEED_CATEGORIES:
            if entry["slug"] in existing_slugs:
                skipped += 1
                continue
            use_case.execute(name=entry["name"], slug=entry["slug"], parent_id=None)
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Done: {created} created, {skipped} skipped."))
