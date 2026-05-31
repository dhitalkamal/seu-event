"""Django admin registrations for events domain models."""

from __future__ import annotations

from django.contrib import admin

from apps.events.infrastructure.models import Event

admin.site.register(Event)
