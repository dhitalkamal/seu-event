"""URL routes for the events app."""

from __future__ import annotations

from django.urls import URLPattern, path

from .views import CreateEventView, HealthCheckView

urlpatterns: list[URLPattern] = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("events/", CreateEventView.as_view(), name="event-create"),
]
