"""URL routes for the events app."""

from __future__ import annotations

from django.urls import URLPattern, path

from .views import (
    AdminEventAnalyticsView,
    CategoryListCreateView,
    CompleteEventView,
    CoverImageUploadView,
    CreateEventView,
    EventDetailView,
    EventMediaDetailView,
    EventMediaListCreateView,
    EventMyView,
    HealthCheckView,
    IcalExportView,
    PublishEventView,
    RegistrationCountView,
    TagListCreateView,
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
    path("categories/", CategoryListCreateView.as_view(), name="category-list-create"),
    path("tags/", TagListCreateView.as_view(), name="tag-list-create"),
    path("uploads/cover/", CoverImageUploadView.as_view(), name="cover-image-upload"),
    path("events/<uuid:event_id>/media/", EventMediaListCreateView.as_view(), name="event-media-list"),
    path(
        "events/<uuid:event_id>/media/<uuid:media_id>/",
        EventMediaDetailView.as_view(),
        name="event-media-detail",
    ),
    path("admin/analytics/", AdminEventAnalyticsView.as_view(), name="admin-event-analytics"),
    path("events/<uuid:event_id>/ical/", IcalExportView.as_view(), name="event-ical-export"),
]
