"""URL routes for the events app."""

from __future__ import annotations

from django.urls import URLPattern, path

from .views import (
    CompleteEventView,
    CreateEventView,
    EventDetailView,
    EventMyView,
    HealthCheckView,
    PublishEventView,
    RegistrationCountView,
)

urlpatterns: list[URLPattern] = [
    path("health/", HealthCheckView.as_view(), name="health"),
    path("events/", CreateEventView.as_view(), name="event-list-create"),
    path("events/my/", EventMyView.as_view(), name="event-my"),
    path("events/<uuid:event_id>/", EventDetailView.as_view(), name="event-detail"),
    path("events/<uuid:event_id>/publish/", PublishEventView.as_view(), name="event-publish"),
    path("events/<uuid:event_id>/complete/", CompleteEventView.as_view(), name="event-complete"),
    path(
        "events/<uuid:event_id>/registration-count/",
        RegistrationCountView.as_view(),
        name="event-registration-count",
    ),
]
