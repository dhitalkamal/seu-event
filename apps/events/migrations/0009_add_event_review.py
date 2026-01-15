"""Migration: add event_review table to the events schema."""

from __future__ import annotations

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    """Creates the EventReview table for post-event ratings."""

    dependencies = [
        ("events", "0008_add_organisation_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="EventReview",
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
                ("event_id", models.UUIDField(db_index=True)),
                ("user_id", models.UUIDField()),
                ("rating", models.PositiveSmallIntegerField()),
                ("highlights", models.JSONField(default=list)),
                ("note", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "db_table": '"events"."event_review"',
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="eventreview",
            constraint=models.UniqueConstraint(
                fields=["event_id", "user_id"],
                name="unique_event_review",
            ),
        ),
    ]
