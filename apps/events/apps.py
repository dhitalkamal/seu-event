"""Django app config for the events module."""
from __future__ import annotations

from django.apps import AppConfig


class EventsConfig(AppConfig):
    """Registers the events app with Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.events"
    label = "events"
