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
from apps.events.application.use_cases.complete_event import CompleteEventUseCase
from apps.events.application.use_cases.create_category import CreateCategoryUseCase
from apps.events.application.use_cases.create_event import CreateEventUseCase
from apps.events.application.use_cases.create_tag import CreateTagUseCase
from apps.events.application.use_cases.delete_event import DeleteEventUseCase
from apps.events.application.use_cases.get_event import GetEventUseCase
from apps.events.application.use_cases.list_categories import ListCategoriesUseCase
from apps.events.application.use_cases.list_events import ListEventsUseCase
from apps.events.application.use_cases.list_my_events import ListMyEventsUseCase
from apps.events.application.use_cases.list_tags import ListTagsUseCase
from apps.events.application.use_cases.publish_event import PublishEventUseCase
from apps.events.application.use_cases.update_event import UpdateEventUseCase
from apps.events.application.use_cases.update_registration_count import (
    UpdateRegistrationCountUseCase,
)
from apps.events.infrastructure.repositories import (
    DjangoCategoryRepository,
    DjangoEventRepository,
    DjangoTagRepository,
)
from apps.events.presentation.serializers import (
    CategoryResponseSerializer,
    CreateCategorySerializer,
    CreateEventSerializer,
    CreateTagSerializer,
    EventFilterSerializer,
    EventResponseSerializer,
    RegistrationCountSerializer,
    TagResponseSerializer,
    UpdateEventSerializer,
)

# anchor variables keep use-case and serializer imports alive through ruff
_PAGINATION_CLASS = StandardPagination
_LIST_EVENTS_UC = ListEventsUseCase
_LIST_MY_UC = ListMyEventsUseCase
_FILTER_SER = EventFilterSerializer
_COMPLETE_UC = CompleteEventUseCase
_COUNT_UC = UpdateRegistrationCountUseCase
_CREATE_CAT_UC = CreateCategoryUseCase
_LIST_CAT_UC = ListCategoriesUseCase
_CREATE_TAG_UC = CreateTagUseCase
_LIST_TAG_UC = ListTagsUseCase

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
    """List published public events or create a new event."""

    permission_classes = [IsAuthenticated]

    def get_permissions(self) -> list:
        """Allow anyone to list events; require auth to create."""
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(
        tags=["Events"],
        summary="List published public events",
        parameters=[_FILTER_SER],
        responses={
            200: OpenApiResponse(
                description="Paginated list of published public events.",
                response=EventResponseSerializer(many=True),
            ),
        },
    )
    def get(self, request: Request) -> Response:
        """Return paginated published public events with optional filters."""
        filter_ser = _FILTER_SER(data=request.query_params)
        filter_ser.is_valid(raise_exception=True)
        f = filter_ser.validated_data
        events = _LIST_EVENTS_UC(DjangoEventRepository()).execute(
            organiser_id=f.get("organiser_id"),
            is_free=f.get("is_free"),
            search=f.get("search"),
            category_id=f.get("category_id"),
            tag_id=f.get("tag_id"),
            date_from=f.get("date_from"),
            date_to=f.get("date_to"),
            location=f.get("location"),
        )
        paginator = _PAGINATION_CLASS()
        page = paginator.paginate_queryset(events, request)
        return paginator.get_paginated_response(EventResponseSerializer(page, many=True).data)

    @extend_schema(
        tags=["Events"],
        summary="Create a new event",
        description=(
            "Creates an event in DRAFT status. "
            "The organiser is inferred from the JWT - no organiser_id in the request body. "
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

        entity = CreateEventUseCase(
            DjangoEventRepository(),
            category_repo=DjangoCategoryRepository(),
            tag_repo=DjangoTagRepository(),
        ).execute(
            organiser_id=uuid.UUID(str(request.user.id)),
            title=d["title"],
            description=d["description"],
            location=d["location"],
            start_date=d["start_date"],
            end_date=d["end_date"],
            capacity=d["capacity"],
            visibility=d["visibility"],
            is_free=d["is_free"],
            price=d.get("price"),
            cover_image=d.get("cover_image"),
            is_online=d.get("is_online", False),
            category_id=d.get("category_id"),
            tag_ids=d.get("tag_ids", []),
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
        entity = UpdateEventUseCase(
            DjangoEventRepository(),
            category_repo=DjangoCategoryRepository(),
            tag_repo=DjangoTagRepository(),
        ).execute(
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


class EventMyView(APIView):
    """List the authenticated organiser's own events across all statuses."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Events"],
        summary="List my events",
        description="Returns all non-deleted events owned by the authenticated organiser.",
        responses={
            200: OpenApiResponse(
                description="Paginated list of own events.",
                response=EventResponseSerializer(many=True),
            ),
            401: OpenApiResponse(description="Missing or invalid JWT."),
        },
    )
    def get(self, request: Request) -> Response:
        """Return paginated list of own events."""
        organiser_id = uuid.UUID(str(request.user.id))
        events = _LIST_MY_UC(DjangoEventRepository()).execute(organiser_id=organiser_id)
        paginator = _PAGINATION_CLASS()
        page = paginator.paginate_queryset(events, request)
        return paginator.get_paginated_response(EventResponseSerializer(page, many=True).data)


class CompleteEventView(APIView):
    """Transition a published event to completed status."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Events"],
        summary="Complete a published event",
        request=None,
        responses={
            200: OpenApiResponse(description="Event completed.", response=EventResponseSerializer),
            401: OpenApiResponse(description="Missing or invalid JWT."),
            403: OpenApiResponse(description="Not the organiser."),
            404: OpenApiResponse(description="Event not found."),
            422: OpenApiResponse(description="Event is not in published status."),
        },
    )
    def post(self, request: Request, event_id: uuid.UUID) -> Response:
        """Mark the published event as completed."""
        entity = _COMPLETE_UC(DjangoEventRepository()).execute(
            event_id=event_id,
            organiser_id=uuid.UUID(str(request.user.id)),
        )
        return success_response(EventResponseSerializer(entity).data, request=request)


class RegistrationCountView(APIView):
    """Internal endpoint for participation-service to sync registered_count."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Internal"],
        summary="Update event registered_count",
        description=(
            "Called by participation-service when a registration is created (+1) "
            "or cancelled (-1). Not for external clients."
        ),
        auth=[],
        request=RegistrationCountSerializer,
        responses={
            200: OpenApiResponse(description="Count updated."),
            404: OpenApiResponse(description="Event not found."),
            422: OpenApiResponse(description="Validation error."),
        },
    )
    def post(self, request: Request, event_id: uuid.UUID) -> Response:
        """Apply delta to event registered_count."""
        ser = RegistrationCountSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        _COUNT_UC(DjangoEventRepository()).execute(
            event_id=event_id,
            delta=ser.validated_data["delta"],
        )
        return success_response({"updated": True}, request=request)


class CategoryListCreateView(APIView):
    """List all categories or create a new one."""

    def get_permissions(self) -> list:
        """Anyone can list; only authenticated users can create."""
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(
        tags=["Categories"],
        summary="List all categories",
        auth=[],
        responses={
            200: OpenApiResponse(
                description="All categories.",
                response=CategoryResponseSerializer(many=True),
            ),
        },
    )
    def get(self, request: Request) -> Response:
        """Return all categories ordered by depth then name."""
        categories = _LIST_CAT_UC(DjangoCategoryRepository()).execute()
        return success_response(
            CategoryResponseSerializer(categories, many=True).data, request=request
        )

    @extend_schema(
        tags=["Categories"],
        summary="Create a category",
        request=CreateCategorySerializer,
        responses={
            201: OpenApiResponse(
                description="Category created.", response=CategoryResponseSerializer
            ),
            401: OpenApiResponse(description="Missing or invalid JWT."),
            422: OpenApiResponse(description="Validation error or depth limit exceeded."),
        },
    )
    def post(self, request: Request) -> Response:
        """Validate payload and persist the new category."""
        ser = CreateCategorySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        entity = _CREATE_CAT_UC(DjangoCategoryRepository()).execute(
            name=d["name"],
            slug=d["slug"],
            parent_id=d.get("parent_id"),
        )
        return created_response(CategoryResponseSerializer(entity).data, request=request)


class TagListCreateView(APIView):
    """List all tags or create a new one."""

    def get_permissions(self) -> list:
        """Anyone can list; only authenticated users can create."""
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(
        tags=["Tags"],
        summary="List all tags",
        auth=[],
        responses={
            200: OpenApiResponse(
                description="All tags.",
                response=TagResponseSerializer(many=True),
            ),
        },
    )
    def get(self, request: Request) -> Response:
        """Return all tags ordered by name."""
        tags = _LIST_TAG_UC(DjangoTagRepository()).execute()
        return success_response(TagResponseSerializer(tags, many=True).data, request=request)

    @extend_schema(
        tags=["Tags"],
        summary="Create a tag",
        request=CreateTagSerializer,
        responses={
            201: OpenApiResponse(description="Tag created.", response=TagResponseSerializer),
            401: OpenApiResponse(description="Missing or invalid JWT."),
            409: OpenApiResponse(description="Slug already exists."),
            422: OpenApiResponse(description="Validation error."),
        },
    )
    def post(self, request: Request) -> Response:
        """Validate payload and persist the new tag."""
        ser = CreateTagSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        entity = _CREATE_TAG_UC(DjangoTagRepository()).execute(
            name=d["name"],
            slug=d["slug"],
        )
        return created_response(TagResponseSerializer(entity).data, request=request)
