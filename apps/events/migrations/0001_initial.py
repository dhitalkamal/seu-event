"""Create the events.event table."""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):
    """Initial events table."""

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Event",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("organiser_id", models.UUIDField()),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField()),
                ("location", models.CharField(max_length=500)),
                ("start_date", models.DateTimeField()),
                ("end_date", models.DateTimeField()),
                ("capacity", models.PositiveIntegerField()),
                ("registered_count", models.PositiveIntegerField(default=0)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Draft"),
                            ("published", "Published"),
                            ("cancelled", "Cancelled"),
                            ("completed", "Completed"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                (
                    "visibility",
                    models.CharField(
                        choices=[
                            ("public", "Public"),
                            ("private", "Private"),
                            ("unlisted", "Unlisted"),
                        ],
                        default="public",
                        max_length=20,
                    ),
                ),
                ("is_free", models.BooleanField(default=True)),
                (
                    "price",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0.00"),
                        max_digits=12,
                    ),
                ),
                ("deleted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "events_event"},
        ),
    ]
