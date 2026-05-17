"""DRF API views for events endpoints."""

from __future__ import annotations

import uuid

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.api.responses import created_response, error_response, success_response
from apps.common.health import check_database, check_rabbitmq, check_redis
from apps.events.application.use_cases.create_event import CreateEventUseCase
from apps.events.application.use_cases.delete_event import DeleteEventUseCase
from apps.events.application.use_cases.get_event import GetEventUseCase
from apps.events.application.use_cases.publish_event import PublishEventUseCase
from apps.events.application.use_cases.update_event import UpdateEventUseCase
from apps.events.infrastructure.repositories import DjangoEventRepository
from apps.events.presentation.serializers import (
    CreateEventSerializer,
    EventResponseSerializer,
    UpdateEventSerializer,
)

_CHECKS = inline_serializer(
    name="DependencyChecks",
    fields={
        "database": serializers.ChoiceField(choices=["healthy", "unhealthy"]),
        "redis": serializers.ChoiceField(choices=["healthy", "unhealthy"]),
        "rabbitmq": serializers.ChoiceField(choices=["healthy", "unhealthy"]),
    },
)
_META_SCHEMA = inline_serializer(
    name="ResponseMeta",
    fields={
        "request_id": serializers.CharField(),
        "timestamp": serializers.CharField(),
    },
)


class HealthCheckView(APIView):
    """Reports the operational status of all external dependencies."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Health"],
        summary="Service health check",
        description=(
            "Checks connectivity to PostgreSQL, Redis, and RabbitMQ. "
            "Returns 200 when all dependencies are healthy, 503 when any are down."
        ),
        auth=[],
        responses={
            200: OpenApiResponse(
                description="All dependencies are healthy.",
                response=inline_serializer(
                    name="HealthyResponse",
                    fields={
                        "data": inline_serializer(
                            name="HealthyData",
                            fields={
                                "service": serializers.CharField(),
                                "status": serializers.CharField(),
                                "version": serializers.CharField(),
                                "checks": _CHECKS,
                            },
                        ),
                        "error": serializers.JSONField(allow_null=True),
                        "meta": _META_SCHEMA,
                    },
                ),
            ),
            503: OpenApiResponse(
                description="One or more dependencies are unavailable.",
                response=inline_serializer(
                    name="UnhealthyResponse",
                    fields={
                        "data": serializers.JSONField(allow_null=True),
                        "error": inline_serializer(
                            name="HealthError",
                            fields={
                                "code": serializers.CharField(),
                                "message": serializers.CharField(),
                                "details": serializers.JSONField(allow_null=True),
                            },
                        ),
                        "meta": _META_SCHEMA,
                    },
                ),
            ),
        },
    )
    def get(self, request: Request) -> Response:
        """Check DB, Redis, and RabbitMQ and return an aggregated status."""
        db_status, db_err = check_database()
        redis_status, redis_err = check_redis()
        rmq_status, rmq_err = check_rabbitmq()

        checks: dict = {
            "database": db_status,
            "redis": redis_status,
            "rabbitmq": rmq_status,
        }
        dep_errors: dict = {
            k: v
            for k, v in {
                "database": db_err,
                "redis": redis_err,
                "rabbitmq": rmq_err,
            }.items()
            if v is not None
        }

        all_healthy = all(s == "healthy" for s in checks.values())

        if all_healthy:
            return success_response(
                {
                    "service": settings.SERVICE_NAME,
                    "status": "healthy",
                    "version": "0.1.0",
                    "checks": checks,
                },
                request=request,
            )

        return error_response(
            code="ERR_SERVICE_UNHEALTHY",
            message="One or more dependencies are unavailable.",
            details={"checks": checks, **({"errors": dep_errors} if dep_errors else {})},
            http_status=503,
            request=request,
        )


class CreateEventView(APIView):
    """Create a new event in DRAFT status owned by the authenticated organiser."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Events"],
        summary="Create a new event",
        description=(
            "Creates an event in DRAFT status. "
            "The organiser is inferred from the JWT — no organiser_id in the request body. "
            "Returns 422 if the payload fails validation or dates are invalid."
        ),
        request=CreateEventSerializer,
        responses={
            201: OpenApiResponse(description="Event created.", response=EventResponseSerializer),
            401: OpenApiResponse(description="Missing or invalid JWT."),
            422: OpenApiResponse(description="Validation error or invalid dates."),
        },
    )
    def post(self, request: Request) -> Response:
        """Validate the payload and persist the event."""
        ser = CreateEventSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        entity = CreateEventUseCase(DjangoEventRepository()).execute(
            organiser_id=uuid.UUID(str(request.user.id)),
            title=d["title"],
            description=d["description"],
            location=d["location"],
            start_date=d["start_date"],
            end_date=d["end_date"],
            capacity=d["capacity"],
            visibility=d["visibility"],
            is_free=d["is_free"],
            price=d["price"],
        )
        return created_response(EventResponseSerializer(entity).data, request=request)


class EventDetailView(APIView):
    """Retrieve, partially update, or soft-delete a single event."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Events"],
        summary="Get event by id",
        responses={
            200: OpenApiResponse(description="Event found.", response=EventResponseSerializer),
            401: OpenApiResponse(description="Missing or invalid JWT."),
            404: OpenApiResponse(description="Event not found."),
        },
    )
    def get(self, request: Request, event_id: uuid.UUID) -> Response:
        """Return the event matching the given id."""
        entity = GetEventUseCase(DjangoEventRepository()).execute(event_id=event_id)
        return success_response(EventResponseSerializer(entity).data, request=request)

    @extend_schema(
        tags=["Events"],
        summary="Partially update an event",
        request=UpdateEventSerializer,
        responses={
            200: OpenApiResponse(description="Event updated.", response=EventResponseSerializer),
            401: OpenApiResponse(description="Missing or invalid JWT."),
            403: OpenApiResponse(description="Not the organiser."),
            404: OpenApiResponse(description="Event not found."),
            422: OpenApiResponse(description="Validation error or invalid dates."),
        },
    )
    def patch(self, request: Request, event_id: uuid.UUID) -> Response:
        """Apply a partial update to the event. Only provided fields are changed."""
        ser = UpdateEventSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        entity = UpdateEventUseCase(DjangoEventRepository()).execute(
            event_id=event_id,
            organiser_id=uuid.UUID(str(request.user.id)),
            **ser.validated_data,
        )
        return success_response(EventResponseSerializer(entity).data, request=request)

    @extend_schema(
        tags=["Events"],
        summary="Soft-delete an event",
        responses={
            204: OpenApiResponse(description="Event deleted."),
            401: OpenApiResponse(description="Missing or invalid JWT."),
            403: OpenApiResponse(description="Not the organiser."),
            404: OpenApiResponse(description="Event not found."),
        },
    )
    def delete(self, request: Request, event_id: uuid.UUID) -> Response:
        """Soft-delete the event by setting deleted_at and status=cancelled."""
        DeleteEventUseCase(DjangoEventRepository()).execute(
            event_id=event_id,
            organiser_id=uuid.UUID(str(request.user.id)),
        )
        return Response(status=204)


class PublishEventView(APIView):
    """Transition a draft event to published status."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Events"],
        summary="Publish a draft event",
        request=None,
        responses={
            200: OpenApiResponse(description="Event published.", response=EventResponseSerializer),
            401: OpenApiResponse(description="Missing or invalid JWT."),
            403: OpenApiResponse(description="Not the organiser."),
            404: OpenApiResponse(description="Event not found."),
            422: OpenApiResponse(description="Invalid status transition or past start date."),
        },
    )
    def post(self, request: Request, event_id: uuid.UUID) -> Response:
        """Publish the event after validating ownership, status, and start date."""
        entity = PublishEventUseCase(DjangoEventRepository()).execute(
            event_id=event_id,
            organiser_id=uuid.UUID(str(request.user.id)),
        )
        return success_response(EventResponseSerializer(entity).data, request=request)
