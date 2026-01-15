"""Django ORM model for event reviews and ratings."""

from __future__ import annotations

import uuid

from django.db import models


class EventReview(models.Model):
    """A user's post-event rating and review.

    Ratings are 1-5 inclusive. Each user can only review a given event once.
    Highlights is a free-form JSON list of tags (e.g. "great venue", "poor audio").
    """

    class Meta:
        db_table = '"events"."event_review"'
        constraints = [
            models.UniqueConstraint(
                fields=["event_id", "user_id"],
                name="unique_event_review",
            )
        ]
        ordering = ["-created_at"]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.UUIDField(db_index=True)
    user_id = models.UUIDField()
    # 1-5 star rating; validated in the view serializer
    rating = models.PositiveSmallIntegerField()
    highlights = models.JSONField(default=list)
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
