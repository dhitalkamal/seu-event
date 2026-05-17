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

from apps.common.api.pagination import StandardPagination
from apps.common.api.responses import created_response, error_response, success_response
from apps.common.health import check_database, check_rabbitmq, check_redis
from apps.events.application.use_cases.create_event import CreateEventUseCase
from apps.events.application.use_cases.delete_event import DeleteEventUseCase
from apps.events.application.use_cases.get_event import GetEventUseCase
from apps.events.application.use_cases.list_events import ListEventsUseCase
from apps.events.application.use_cases.list_my_events import ListMyEventsUseCase
from apps.events.application.use_cases.publish_event import PublishEventUseCase
from apps.events.application.use_cases.update_event import UpdateEventUseCase
from apps.events.infrastructure.repositories import DjangoEventRepository
from apps.events.presentation.serializers import (
    CreateEventSerializer,
    EventFilterSerializer,
    EventResponseSerializer,
    UpdateEventSerializer,
)

# shared schema building blocks
_META = inline_serializer(
    name="EventResponseMeta",
    fields={
        "request_id": serializers.CharField(),
        "timestamp": serializers.CharField(),
    },
)

_ERROR_ENVELOPE = inline_serializer(
    name="EventErrorEnvelope",
    fields={
        "data": serializers.JSONField(allow_null=True, default=None),
        "error": inline_serializer(
            name="EventErrorEnvelopeBody",
            fields={
                "code": serializers.CharField(help_text="Machine-readable error code."),
                "message": serializers.CharField(help_text="Human-readable error description."),
                "details": serializers.JSONField(
                    allow_null=True,
                    help_text="Extra context: flat list of {field, message} for validation errors.",
                ),
            },
        ),
        "meta": _META,
    },
)

_MSG_ENVELOPE = inline_serializer(
    name="EventMessageEnvelope",
    fields={
        "data": inline_serializer(
            name="EventMessageData",
            fields={"message": serializers.CharField()},
        ),
        "error": serializers.JSONField(allow_null=True, default=None),
        "meta": _META,
    },
)

_CHECKS = inline_serializer(
    name="EventDependencyChecks",
    fields={
        "database": serializers.ChoiceField(choices=["healthy", "unhealthy"]),
        "redis": serializers.ChoiceField(choices=["healthy", "unhealthy"]),
        "rabbitmq": serializers.ChoiceField(choices=["healthy", "unhealthy"]),
    },
)

_PAGINATED_EVENTS = inline_serializer(
    name="PaginatedEventList",
    fields={
        "count": serializers.IntegerField(help_text="Total number of matching events."),
        "next": serializers.URLField(allow_null=True, help_text="URL of the next page, or null."),
        "previous": serializers.URLField(
            allow_null=True, help_text="URL of the previous page, or null."
        ),
        "results": EventResponseSerializer(many=True),
    },
)

# reusable per-status OpenApiResponse objects
_R401 = OpenApiResponse(
    description="Authentication credentials are missing or invalid.",
    response=_ERROR_ENVELOPE,
)
_R403 = OpenApiResponse(
    description="You are not the organiser of this event.",
    response=_ERROR_ENVELOPE,
)
_R404 = OpenApiResponse(
    description="Event not found.",
    response=_ERROR_ENVELOPE,
)
_R422 = OpenApiResponse(
    description="Payload failed validation or a business rule was violated. "
    "details contains a flat list of {field, message} objects.",
    response=_ERROR_ENVELOPE,
)
_R503 = OpenApiResponse(
    description="One or more dependencies are unavailable.",
    response=_ERROR_ENVELOPE,
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
                    name="EventHealthSuccessEnvelope",
                    fields={
                        "data": inline_serializer(
                            name="EventHealthData",
                            fields={
                                "service": serializers.CharField(),
                                "status": serializers.CharField(),
                                "version": serializers.CharField(),
                                "checks": _CHECKS,
                            },
                        ),
                        "error": serializers.JSONField(allow_null=True, default=None),
                        "meta": _META,
                    },
                ),
            ),
            503: _R503,
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

        if all(s == "healthy" for s in checks.values()):
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
    """List published public events or create a new draft event."""

    permission_classes = [IsAuthenticated]

    def get_permissions(self) -> list:
        """Allow anyone to list events; require auth to create."""
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(
        tags=["Events"],
        summary="List published public events",
        description=(
            "Returns a paginated list of published public events. "
            "Optionally filter by organiser_id, is_free, or title search."
        ),
        auth=[],
        parameters=[EventFilterSerializer],
        responses={
            200: OpenApiResponse(
                description="Paginated list of published public events.",
                response=_PAGINATED_EVENTS,
            ),
            422: _R422,
        },
    )
    def get(self, request: Request) -> Response:
        """Return paginated published public events with optional filters."""
        filter_ser = EventFilterSerializer(data=request.query_params)
        filter_ser.is_valid(raise_exception=True)
        f = filter_ser.validated_data
        events = ListEventsUseCase(DjangoEventRepository()).execute(
            organiser_id=f.get("organiser_id"),
            is_free=f.get("is_free"),
            search=f.get("search"),
        )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(events, request)
        return paginator.get_paginated_response(EventResponseSerializer(page, many=True).data)

    @extend_schema(
        tags=["Events"],
        summary="Create a new event",
        description=(
            "Creates an event in DRAFT status owned by the authenticated user. "
            "The organiser_id is inferred from the JWT — do not include it in the body. "
            "Call POST /events/{id}/publish/ to make the event publicly visible."
        ),
        request=CreateEventSerializer,
        responses={
            201: OpenApiResponse(
                description="Event created in DRAFT status.",
                response=inline_serializer(
                    name="EventCreateEnvelope",
                    fields={
                        "data": EventResponseSerializer(),
                        "error": serializers.JSONField(allow_null=True, default=None),
                        "meta": _META,
                    },
                ),
            ),
            401: _R401,
            422: _R422,
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

    def get_permissions(self) -> list:
        """Allow anyone to read event details; require auth to modify."""
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(
        tags=["Events"],
        summary="Get event by ID",
        description="Returns the full detail of a single event. Accessible without authentication.",
        auth=[],
        responses={
            200: OpenApiResponse(
                description="Event detail.",
                response=inline_serializer(
                    name="EventGetEnvelope",
                    fields={
                        "data": EventResponseSerializer(),
                        "error": serializers.JSONField(allow_null=True, default=None),
                        "meta": _META,
                    },
                ),
            ),
            404: _R404,
        },
    )
    def get(self, request: Request, event_id: uuid.UUID) -> Response:
        """Return the event matching the given ID."""
        entity = GetEventUseCase(DjangoEventRepository()).execute(event_id=event_id)
        return success_response(EventResponseSerializer(entity).data, request=request)

    @extend_schema(
        tags=["Events"],
        summary="Update an event",
        description=(
            "Partially update any field on an event. Only the organiser can update. "
            "Only provided fields are changed; omitted fields retain their current values. "
            "Start/end date changes are re-validated against business rules."
        ),
        request=UpdateEventSerializer,
        responses={
            200: OpenApiResponse(
                description="Updated event.",
                response=inline_serializer(
                    name="EventPatchEnvelope",
                    fields={
                        "data": EventResponseSerializer(),
                        "error": serializers.JSONField(allow_null=True, default=None),
                        "meta": _META,
                    },
                ),
            ),
            401: _R401,
            403: _R403,
            404: _R404,
            422: _R422,
        },
    )
    def patch(self, request: Request, event_id: uuid.UUID) -> Response:
        """Apply a partial update to the event."""
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
        summary="Delete an event",
        description=(
            "Soft-deletes the event by setting status=cancelled and recording deleted_at. "
            "Only the organiser can delete. "
            "Deleted events are excluded from all listing endpoints."
        ),
        responses={
            204: OpenApiResponse(description="Event deleted successfully. No response body."),
            401: _R401,
            403: _R403,
            404: _R404,
        },
    )
    def delete(self, request: Request, event_id: uuid.UUID) -> Response:
        """Soft-delete the event."""
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
        summary="Publish an event",
        description=(
            "Transitions the event from DRAFT to PUBLISHED, making it publicly visible. "
            "Only the organiser can publish. "
            "Returns 422 if the event is not in DRAFT status, "
            "or if start_date is in the past."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                description="Event published and now publicly visible.",
                response=inline_serializer(
                    name="EventPublishEnvelope",
                    fields={
                        "data": EventResponseSerializer(),
                        "error": serializers.JSONField(allow_null=True, default=None),
                        "meta": _META,
                    },
                ),
            ),
            401: _R401,
            403: _R403,
            404: _R404,
            422: _R422,
        },
    )
    def post(self, request: Request, event_id: uuid.UUID) -> Response:
        """Publish the event after validating ownership, status, and start date."""
        entity = PublishEventUseCase(DjangoEventRepository()).execute(
            event_id=event_id,
            organiser_id=uuid.UUID(str(request.user.id)),
        )
        return success_response(EventResponseSerializer(entity).data, request=request)


class EventMyView(APIView):
    """List the authenticated organiser's own events across all statuses."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Events"],
        summary="List my events",
        description=(
            "Returns a paginated list of all non-deleted events owned by the authenticated user, "
            "across all statuses (draft, published, cancelled, completed). "
            "Ordered by most recently created first."
        ),
        responses={
            200: OpenApiResponse(
                description="Paginated list of own events.",
                response=_PAGINATED_EVENTS,
            ),
            401: _R401,
        },
    )
    def get(self, request: Request) -> Response:
        """Return paginated list of own events."""
        organiser_id = uuid.UUID(str(request.user.id))
        events = ListMyEventsUseCase(DjangoEventRepository()).execute(organiser_id=organiser_id)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(events, request)
        return paginator.get_paginated_response(EventResponseSerializer(page, many=True).data)
