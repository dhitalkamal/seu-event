"""URL routes for the events app."""

from __future__ import annotations

from django.urls import URLPattern, path

from .views import CreateEventView, EventDetailView, EventMyView, HealthCheckView, PublishEventView

urlpatterns: list[URLPattern] = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("events/", CreateEventView.as_view(), name="event-list-create"),
    path("events/my/", EventMyView.as_view(), name="event-my"),
    path("events/<uuid:event_id>/", EventDetailView.as_view(), name="event-detail"),
    path("events/<uuid:event_id>/publish/", PublishEventView.as_view(), name="event-publish"),
]
