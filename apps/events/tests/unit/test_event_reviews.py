"""Tests for EventReview model and endpoints (item 18)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from apps.events.infrastructure.review_models import EventReview


class TestEventReviewModel:
    """Model-level tests for EventReview."""

    def test_model_has_expected_fields(self) -> None:
        """EventReview must have event_id, user_id, rating, highlights, note, created_at."""
        assert hasattr(EventReview, "event_id")
        assert hasattr(EventReview, "user_id")
        assert hasattr(EventReview, "rating")
        assert hasattr(EventReview, "highlights")
        assert hasattr(EventReview, "note")
        assert hasattr(EventReview, "created_at")

    def test_model_meta_table_name(self) -> None:
        """EventReview must use the events schema."""
        assert EventReview._meta.db_table == "events_event_review"

    def test_model_unique_together_constraint(self) -> None:
        """Each (event_id, user_id) pair must be unique."""
        constraint_fields = [list(constraint.fields) for constraint in EventReview._meta.constraints]
        assert ["event_id", "user_id"] in constraint_fields


class TestEventReviewEndpoints:
    """Unit tests for the EventReview API views."""

    def _make_request(self, method: str, path: str, data: dict | None = None) -> object:
        """Build an authenticated DRF request."""
        from rest_framework.parsers import JSONParser
        from rest_framework.request import Request
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        if method == "post":
            django_request = factory.post(path, data=data or {}, format="json")
        else:
            django_request = factory.get(path)

        request = Request(django_request, parsers=[JSONParser()])
        fake_user = MagicMock()
        fake_user.id = str(uuid.uuid4())
        fake_user.is_authenticated = True
        request._user = fake_user
        return request

    def test_submit_review_returns_201(self) -> None:
        """POST /events/{id}/reviews/ must return 201 on success."""
        from apps.events.presentation.views import EventReviewListCreateView

        event_id = uuid.uuid4()
        request = self._make_request(
            "post",
            f"/api/v1/events/{event_id}/reviews/",
            {"rating": 4, "highlights": ["great venue"], "note": "Loved it"},
        )

        with patch("apps.events.presentation.views.EventReview") as mock_model:
            mock_instance = MagicMock()
            mock_instance.id = uuid.uuid4()
            mock_instance.rating = 4
            mock_instance.highlights = ["great venue"]
            mock_instance.note = "Loved it"
            mock_instance.created_at = MagicMock()
            mock_instance.created_at.isoformat.return_value = "2026-01-01T00:00:00Z"
            mock_model.objects.filter.return_value.exists.return_value = False
            mock_model.objects.create.return_value = mock_instance

            view = EventReviewListCreateView()
            view.permission_classes = []
            view.authentication_classes = []
            view.kwargs = {}
            view.args = ()
            view.request = request
            view.format_kwarg = None
            view.headers = {}

            response = view.post(request, event_id=event_id)

        assert response.status_code == 201

    def test_list_reviews_returns_200(self) -> None:
        """GET /events/{id}/reviews/ must return 200 with list."""
        from apps.events.presentation.views import EventReviewListCreateView

        event_id = uuid.uuid4()
        request = self._make_request("get", f"/api/v1/events/{event_id}/reviews/")

        with patch("apps.events.presentation.views.EventReview") as mock_model:
            mock_model.objects.filter.return_value.order_by.return_value = []

            view = EventReviewListCreateView()
            view.permission_classes = []
            view.authentication_classes = []
            view.kwargs = {}
            view.args = ()
            view.request = request
            view.format_kwarg = None
            view.headers = {}

            response = view.get(request, event_id=event_id)

        assert response.status_code == 200

    def test_review_summary_returns_200(self) -> None:
        """GET /events/{id}/reviews/summary/ must return 200 with avg and count."""
        from apps.events.presentation.views import EventReviewSummaryView

        event_id = uuid.uuid4()
        request = self._make_request("get", f"/api/v1/events/{event_id}/reviews/summary/")

        with patch("apps.events.presentation.views.EventReview") as mock_model:
            mock_model.objects.filter.return_value.aggregate.return_value = {
                "avg_rating": 4.2,
                "count": 5,
            }

            view = EventReviewSummaryView()
            view.permission_classes = []
            view.authentication_classes = []
            view.kwargs = {}
            view.args = ()
            view.request = request
            view.format_kwarg = None
            view.headers = {}

            response = view.get(request, event_id=event_id)

        assert response.status_code == 200

    def test_submit_review_rating_out_of_range_raises_validation_error(self) -> None:
        """POST with rating > 5 must raise DRF ValidationError (400)."""
        from rest_framework.exceptions import ValidationError

        from apps.events.presentation.views import EventReviewListCreateView

        event_id = uuid.uuid4()
        request = self._make_request(
            "post",
            f"/api/v1/events/{event_id}/reviews/",
            {"rating": 99},
        )

        view = EventReviewListCreateView()
        view.permission_classes = []
        view.authentication_classes = []
        view.kwargs = {}
        view.args = ()
        view.request = request
        view.format_kwarg = None
        view.headers = {}

        with pytest.raises(ValidationError):
            view.post(request, event_id=event_id)

    def test_submit_review_already_exists_returns_409(self) -> None:
        """POST when user already reviewed this event must return 409."""
        from apps.events.presentation.views import EventReviewListCreateView

        event_id = uuid.uuid4()
        request = self._make_request(
            "post",
            f"/api/v1/events/{event_id}/reviews/",
            {"rating": 3, "highlights": [], "note": ""},
        )

        with patch("apps.events.presentation.views.EventReview") as mock_model:
            mock_model.objects.filter.return_value.exists.return_value = True

            view = EventReviewListCreateView()
            view.permission_classes = []
            view.authentication_classes = []
            view.kwargs = {}
            view.args = ()
            view.request = request
            view.format_kwarg = None
            view.headers = {}

            response = view.post(request, event_id=event_id)

        assert response.status_code == 409
