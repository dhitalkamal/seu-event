"""URL patterns for all events endpoints under /api/v1/."""
from __future__ import annotations

from django.urls import URLPattern, path

from .views import HealthCheckView

urlpatterns: list[URLPattern] = [
    path("health/", HealthCheckView.as_view(), name="health"),
]
