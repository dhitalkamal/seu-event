"""Migration: add online_url to events and create event_media gallery table."""

from __future__ import annotations

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("events", "0006_add_allowed_domains_to_event"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="online_url",
            field=models.URLField(blank=True, max_length=2048, null=True),
        ),
        migrations.CreateModel(
            name="EventMedia",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="media",
                        to="events.event",
                    ),
                ),
                ("url", models.URLField(max_length=2048)),
                (
                    "media_type",
                    models.CharField(
                        choices=[("image", "Image"), ("video", "Video")],
                        default="image",
                        max_length=10,
                    ),
                ),
                ("caption", models.CharField(blank=True, default="", max_length=255)),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "events_event_media", "ordering": ["position"]},
        ),
    ]
