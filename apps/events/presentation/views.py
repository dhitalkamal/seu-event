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
from apps.common.permissions import IsOrgManager
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
from apps.events.infrastructure.audit_publisher import publish_audit
from apps.events.infrastructure.event_publisher import EventPublisher
from apps.events.infrastructure.models import EventMedia
from apps.events.infrastructure.repositories import (
    DjangoCategoryRepository,
    DjangoEventRepository,
    DjangoTagRepository,
)
from apps.events.infrastructure.review_models import EventReview
from apps.events.infrastructure.search_index import ElasticsearchEventIndex
from apps.events.presentation.serializers import (
    CategoryResponseSerializer,
    CreateCategorySerializer,
    CreateEventSerializer,
    CreateTagSerializer,
    EventFilterSerializer,
    EventMediaSerializer,
    EventResponseSerializer,
    RegistrationCountSerializer,
    TagResponseSerializer,
    UpdateEventSerializer,
)


def _has_org_permission(request: Request, organization_id: uuid.UUID) -> bool:
    """
    Return True when the request carries manager-or-higher org role for the organization.

    Used by mutation views when an event belongs to an organization.
    Builds a throwaway view-like object so IsOrgManager can extract org_id normally.
    """

    class _FakeView:
        org_id: uuid.UUID = organization_id
        kwargs: dict = {}

    return IsOrgManager().has_permission(request, _FakeView())  # type: ignore[arg-type]


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
            "Checks connectivity to PostgreSQL, Redis, and RabbitMQ. Returns 200 when all dependencies are healthy, 503 when any are down."
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

        # extract email domain from JWT for domain-restricted event visibility
        user_email_domain: str | None = None
        if request.user and hasattr(request.user, "token"):
            try:
                email: str = request.user.token.get("email", "") or ""
                if "@" in email:
                    user_email_domain = email.split("@", 1)[1].lower()
            except Exception:
                pass

        events = _LIST_EVENTS_UC(DjangoEventRepository()).execute(
            organizer_id=f.get("organizer_id"),
            is_free=f.get("is_free"),
            search=f.get("search"),
            category_id=f.get("category_id"),
            tag_id=f.get("tag_id"),
            date_from=f.get("date_from"),
            date_to=f.get("date_to"),
            location=f.get("location"),
            user_email_domain=user_email_domain,
            lat=f.get("lat"),
            lng=f.get("lng"),
            radius_km=f.get("radius_km"),
            sort_by=f.get("sort_by"),
        )
        paginator = _PAGINATION_CLASS()
        page = paginator.paginate_queryset(events, request)
        return paginator.get_paginated_response(EventResponseSerializer(page, many=True).data)

    @extend_schema(
        tags=["Events"],
        summary="Create a new event",
        description=(
            "Creates an event in DRAFT status. "
            "The organizer is inferred from the JWT - no organizer_id in the request body. "
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
            organizer_id=uuid.UUID(str(request.user.id)),
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
            allowed_domains=d.get("allowed_domains", []),
            organization_id=d.get("organization_id"),
            event_mode=d.get("event_mode", "physical"),
            virtual_capacity=d.get("virtual_capacity"),
            overbooking_percent=d.get("overbooking_percent", 0),
        )
        # auto-create notification journey for this event
        try:
            import json as _json
            import urllib.request as _urllib
            req = _urllib.Request(
                f"http://notification:8005/api/v1/journeys/events/{entity.id}/",
                data=_json.dumps({"event_id": str(entity.id)}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            _urllib.urlopen(req, timeout=5)
        except Exception:
            pass

        publish_audit(
            request=request,
            user_id=uuid.UUID(str(request.user.id)),
            event_type="event.created",
            metadata={"event_id": str(entity.id), "title": entity.title},
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
            403: OpenApiResponse(description="Not the organizer."),
            404: OpenApiResponse(description="Event not found."),
            422: OpenApiResponse(description="Validation error or invalid dates."),
        },
    )
    def patch(self, request: Request, event_id: uuid.UUID) -> Response:
        """Apply a partial update to the event. Only provided fields are changed."""
        ser = UpdateEventSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        # load event first to choose the correct auth path
        repo = DjangoEventRepository()
        event = GetEventUseCase(repo).execute(event_id=event_id)

        if event.organization_id is not None:
            # org-owned event: manager-or-higher role is sufficient
            if not _has_org_permission(request, event.organization_id):
                return error_response(
                    code="ERR_EVENT_NOT_OWNED",
                    message="Insufficient org role to update this event.",
                    http_status=403,
                    request=request,
                )
            effective_organizer_id = event.organizer_id
        else:
            # legacy individual-owned event: must be the organizer
            effective_organizer_id = uuid.UUID(str(request.user.id))

        entity = UpdateEventUseCase(
            repo,
            category_repo=DjangoCategoryRepository(),
            tag_repo=DjangoTagRepository(),
        ).execute(
            event_id=event_id,
            organizer_id=effective_organizer_id,
            **ser.validated_data,
        )
        # notify downstream services (notification-service creates attendee in-app alerts)
        EventPublisher().publish_event_updated(
            event_id=entity.id,
            organizer_id=entity.organizer_id,
            title=entity.title,
        )
        publish_audit(
            request=request,
            user_id=uuid.UUID(str(request.user.id)),
            event_type="event.updated",
            metadata={"event_id": str(entity.id), "title": entity.title},
        )
        return success_response(EventResponseSerializer(entity).data, request=request)

    @extend_schema(
        tags=["Events"],
        summary="Soft-delete an event",
        responses={
            204: OpenApiResponse(description="Event deleted."),
            401: OpenApiResponse(description="Missing or invalid JWT."),
            403: OpenApiResponse(description="Not the organizer."),
            404: OpenApiResponse(description="Event not found."),
        },
    )
    def delete(self, request: Request, event_id: uuid.UUID) -> Response:
        """Soft-delete the event by setting deleted_at and status=cancelled."""
        repo = DjangoEventRepository()
        event = GetEventUseCase(repo).execute(event_id=event_id)

        if event.organization_id is not None:
            if not _has_org_permission(request, event.organization_id):
                return error_response(
                    code="ERR_EVENT_NOT_OWNED",
                    message="Insufficient org role to delete this event.",
                    http_status=403,
                    request=request,
                )
            effective_organizer_id = event.organizer_id
        else:
            effective_organizer_id = uuid.UUID(str(request.user.id))

        DeleteEventUseCase(repo).execute(
            event_id=event_id,
            organizer_id=effective_organizer_id,
        )
        publish_audit(
            request=request,
            user_id=uuid.UUID(str(request.user.id)),
            event_type="event.deleted",
            metadata={"event_id": str(event_id)},
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
            403: OpenApiResponse(description="Not the organizer."),
            404: OpenApiResponse(description="Event not found."),
            422: OpenApiResponse(description="Invalid status transition or past start date."),
        },
    )
    def post(self, request: Request, event_id: uuid.UUID) -> Response:
        """Publish the event after validating ownership, status, and start date."""
        repo = DjangoEventRepository()
        event = GetEventUseCase(repo).execute(event_id=event_id)

        if event.organization_id is not None:
            if not _has_org_permission(request, event.organization_id):
                return error_response(
                    code="ERR_EVENT_NOT_OWNED",
                    message="Insufficient org role to publish this event.",
                    http_status=403,
                    request=request,
                )
            effective_organizer_id = event.organizer_id
        else:
            effective_organizer_id = uuid.UUID(str(request.user.id))

        entity = PublishEventUseCase(repo, search_index=ElasticsearchEventIndex()).execute(
            event_id=event_id,
            organizer_id=effective_organizer_id,
        )
        # broadcast event.published for notification-service
        try:
            from apps.events.infrastructure.event_publisher import EventPublisher
            EventPublisher().publish_event_published(
                event_id=entity.id,
                organizer_id=entity.organizer_id,
                title=entity.title,
            )
        except Exception:
            pass

        # auto-create notification journey (reminders before/after event)
        try:
            import json
            import urllib.request as _urllib
            notification_url = f"http://notification:8005/api/v1/journeys/events/{entity.id}/"
            req = _urllib.Request(
                notification_url,
                data=json.dumps({"event_id": str(entity.id)}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            _urllib.urlopen(req, timeout=5)
        except Exception:
            pass

        publish_audit(
            request=request,
            user_id=uuid.UUID(str(request.user.id)),
            event_type="event.published",
            metadata={"event_id": str(entity.id), "title": entity.title},
        )
        return success_response(EventResponseSerializer(entity).data, request=request)


class EventMyView(APIView):
    """List the authenticated organizer's own events across all statuses."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Events"],
        summary="List my events",
        description="Returns all non-deleted events owned by the authenticated organizer.",
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
        organizer_id = uuid.UUID(str(request.user.id))
        events = _LIST_MY_UC(DjangoEventRepository()).execute(organizer_id=organizer_id)
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
            403: OpenApiResponse(description="Not the organizer."),
            404: OpenApiResponse(description="Event not found."),
            422: OpenApiResponse(description="Event is not in published status."),
        },
    )
    def post(self, request: Request, event_id: uuid.UUID) -> Response:
        """Mark the published event as completed."""
        entity = _COMPLETE_UC(DjangoEventRepository()).execute(
            event_id=event_id,
            organizer_id=uuid.UUID(str(request.user.id)),
        )
        publish_audit(
            request=request,
            user_id=uuid.UUID(str(request.user.id)),
            event_type="event.completed",
            metadata={"event_id": str(entity.id)},
        )
        return success_response(EventResponseSerializer(entity).data, request=request)


class RegistrationCountView(APIView):
    """Internal endpoint for participation-service to sync registered_count."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Internal"],
        summary="Update event registered_count",
        description=("Called by participation-service when a registration is created (+1) or cancelled (-1). Not for external clients."),
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
        return success_response(CategoryResponseSerializer(categories, many=True).data, request=request)

    @extend_schema(
        tags=["Categories"],
        summary="Create a category",
        request=CreateCategorySerializer,
        responses={
            201: OpenApiResponse(description="Category created.", response=CategoryResponseSerializer),
            401: OpenApiResponse(description="Missing or invalid JWT."),
            422: OpenApiResponse(description="Validation error or depth limit exceeded."),
        },
    )
    def post(self, request: Request) -> Response:
        """Validate payload and persist the new category."""
        from django.db import IntegrityError

        ser = CreateCategorySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            entity = _CREATE_CAT_UC(DjangoCategoryRepository()).execute(
                name=d["name"],
                slug=d["slug"],
                parent_id=d.get("parent_id"),
            )
        except IntegrityError:
            return error_response(
                code="ERR_DUPLICATE",
                message=f"Category with slug '{d['slug']}' already exists.",
                http_status=409,
                request=request,
            )
        publish_audit(
            request=request,
            user_id=uuid.UUID(str(request.user.id)),
            event_type="category.created",
            metadata={"category_id": str(entity.id), "name": entity.name, "slug": entity.slug},
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
        from django.db import IntegrityError

        ser = CreateTagSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            entity = _CREATE_TAG_UC(DjangoTagRepository()).execute(
                name=d["name"],
                slug=d["slug"],
            )
        except IntegrityError:
            return error_response(
                code="ERR_DUPLICATE",
                message=f"Tag with slug '{d['slug']}' already exists.",
                http_status=409,
                request=request,
            )
        publish_audit(
            request=request,
            user_id=uuid.UUID(str(request.user.id)),
            event_type="tag.created",
            metadata={"tag_id": str(entity.id), "name": entity.name, "slug": entity.slug},
        )
        return created_response(TagResponseSerializer(entity).data, request=request)


class CoverImageUploadView(APIView):
    """Upload a cover image to MinIO and return the public URL."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Uploads"],
        summary="Upload cover image",
        request=inline_serializer(
            name="CoverImageUploadRequest",
            fields={"file": serializers.ImageField()},
        ),
        responses={
            200: OpenApiResponse(
                description="Upload successful.",
                response=inline_serializer(
                    name="CoverImageUploadResponse",
                    fields={"url": serializers.URLField()},
                ),
            ),
            400: OpenApiResponse(description="No file provided or invalid type."),
            401: OpenApiResponse(description="Missing or invalid JWT."),
        },
    )
    def post(self, request: Request) -> Response:
        """Upload the image file and return its public MinIO URL."""
        from apps.events.infrastructure.storage import upload_image

        file = request.FILES.get("file")
        if not file:
            return error_response(
                code="ERR_EVENT_NO_FILE",
                message="No file provided.",
                http_status=400,
                request=request,
            )
        content_type = file.content_type or "application/octet-stream"
        if not content_type.startswith("image/"):
            return error_response(
                code="ERR_EVENT_INVALID_FILE_TYPE",
                message="Only image files are accepted.",
                http_status=400,
                request=request,
            )
        extension = content_type.split("/")[-1].replace("jpeg", "jpg")
        url = upload_image(
            file_data=file.read(),
            content_type=content_type,
            extension=extension,
        )
        return success_response({"url": url}, request=request)


# Gallery and media views


class EventMediaListCreateView(APIView):
    """List all media for an event or add a new one."""

    def get_permissions(self) -> list:
        """GET is public; POST requires authentication."""
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(tags=["Events"], summary="List event gallery")
    def get(self, request: Request, event_id: uuid.UUID) -> Response:
        """Return all media items for the event ordered by position."""
        items = EventMedia.objects.filter(event_id=event_id).order_by("position")
        data = [
            {
                "id": str(m.id),
                "event_id": str(m.event_id),
                "url": m.url,
                "media_type": m.media_type,
                "caption": m.caption,
                "position": m.position,
                "created_at": m.created_at.isoformat(),
            }
            for m in items
        ]
        return success_response(data, request=request)

    @extend_schema(tags=["Events"], summary="Add event gallery item")
    def post(self, request: Request, event_id: uuid.UUID) -> Response:
        """Add a media item to the event gallery. Enforces a maximum of 20 images per event."""
        # ! hard cap: no more than 20 images per event
        existing_count = EventMedia.objects.filter(event_id=event_id, media_type="image").count()
        if existing_count >= 20:
            return error_response(
                code="ERR_EVENT_MEDIA_LIMIT",
                message="Maximum of 20 images per event has been reached.",
                http_status=400,
                request=request,
            )

        ser = EventMediaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        media = EventMedia.objects.create(
            event_id=event_id,
            url=d["url"],
            media_type=d.get("media_type", "image"),
            caption=d.get("caption", ""),
            position=d.get("position", 0),
        )
        return created_response(
            {
                "id": str(media.id),
                "event_id": str(media.event_id),
                "url": media.url,
                "media_type": media.media_type,
                "caption": media.caption,
                "position": media.position,
                "thumbnail_urls": media.thumbnail_urls,
                "created_at": media.created_at.isoformat(),
            },
            request=request,
        )


class EventMediaDetailView(APIView):
    """Update or delete a single gallery item."""

    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Events"], summary="Update event gallery item")
    def patch(self, request: Request, event_id: uuid.UUID, media_id: uuid.UUID) -> Response:
        """Update caption or position of a media item."""
        try:
            media = EventMedia.objects.get(id=media_id, event_id=event_id)
        except EventMedia.DoesNotExist:
            return error_response(
                code="ERR_EVENT_MEDIA_NOT_FOUND",
                message="Media item not found.",
                http_status=404,
                request=request,
            )
        for field in ("caption", "position"):
            if field in request.data:
                setattr(media, field, request.data[field])
        media.save()
        return success_response(
            {"id": str(media.id), "caption": media.caption, "position": media.position},
            request=request,
        )

    @extend_schema(tags=["Events"], summary="Delete event gallery item")
    def delete(self, request: Request, event_id: uuid.UUID, media_id: uuid.UUID) -> Response:
        """Remove a media item from the event gallery."""
        try:
            EventMedia.objects.get(id=media_id, event_id=event_id).delete()
        except EventMedia.DoesNotExist:
            return error_response(
                code="ERR_EVENT_MEDIA_NOT_FOUND",
                message="Media item not found.",
                http_status=404,
                request=request,
            )
        return success_response({"deleted": True}, request=request)


class AdminEventAnalyticsView(APIView):
    """GET /admin/analytics/ - monthly event stats for the superadmin dashboard."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Admin"],
        summary="Platform event analytics",
        description="Monthly event series, 30-day growth, and top events by registration. Staff only.",
        responses={200: OpenApiResponse(description="Aggregated event analytics.")},
    )
    def get(self, request: Request) -> Response:
        """Return monthly event counts, 30D growth, and top events. Staff only."""
        if not request.user.is_staff:  # type: ignore[union-attr]
            return error_response(code="ERR_FORBIDDEN", message="Staff access required.", http_status=403, request=request)

        from datetime import datetime, timedelta, timezone

        from django.db.models import Count
        from django.db.models.functions import TruncMonth

        from apps.events.infrastructure.models import Event as EventModel

        now = datetime.now(timezone.utc)
        d30 = now - timedelta(days=30)
        d60 = now - timedelta(days=60)
        d365 = now - timedelta(days=365)

        new_30d = EventModel.objects.filter(created_at__gte=d30).count()
        prev_30d = EventModel.objects.filter(created_at__gte=d60, created_at__lt=d30).count()
        total = EventModel.objects.count()

        monthly_qs = (
            EventModel.objects.filter(created_at__gte=d365)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")
        )
        month_map = {row["month"].strftime("%Y-%m"): row["count"] for row in monthly_qs}

        series = []
        for i in range(11, -1, -1):
            dt = now.replace(day=1) - timedelta(days=30 * i)
            key = dt.strftime("%Y-%m")
            series.append(month_map.get(key, 0))

        top_events = list(
            EventModel.objects.filter(registered_count__gt=0)
            .order_by("-registered_count")[:10]
            .values("id", "title", "organization_id", "registered_count", "status", "visibility")
        )

        return success_response(
            {
                "new_events_30d": new_30d,
                "prev_events_30d": prev_30d,
                "total_events": total,
                "monthly_series": series,
                "top_events": [
                    {**e, "id": str(e["id"]), "organization_id": str(e["organization_id"]) if e["organization_id"] else None}
                    for e in top_events
                ],
            },
            request=request,
        )


class EventReviewListCreateView(APIView):
    """Submit a review (POST) or list reviews (GET) for a specific event."""

    def get_permissions(self) -> list:
        """Anyone can read reviews; only authenticated users can submit."""
        if self.request.method == "GET":
            return [AllowAny()]
        return [IsAuthenticated()]

    @extend_schema(
        tags=["Reviews"],
        summary="List event reviews",
        description="Returns all reviews for the given event, newest first.",
        responses={
            200: OpenApiResponse(description="Review list returned."),
        },
    )
    def get(self, request: Request, event_id: uuid.UUID) -> Response:
        """Return all reviews for the event."""
        reviews = EventReview.objects.filter(event_id=event_id).order_by("-created_at")
        data = [
            {
                "id": str(r.id),
                "event_id": str(r.event_id),
                "user_id": str(r.user_id),
                "rating": r.rating,
                "highlights": r.highlights,
                "note": r.note,
                "created_at": r.created_at.isoformat(),
            }
            for r in reviews
        ]
        return success_response(data, request=request)

    @extend_schema(
        tags=["Reviews"],
        summary="Submit an event review",
        description=(
            "Submit a 1-5 star rating plus optional highlights and note for a completed event. "
            "Each user can submit at most one review per event."
        ),
        responses={
            201: OpenApiResponse(description="Review submitted."),
            401: OpenApiResponse(description="Missing or invalid JWT."),
            409: OpenApiResponse(description="User already reviewed this event."),
            422: OpenApiResponse(description="Validation error (e.g. rating out of range)."),
        },
    )
    def post(self, request: Request, event_id: uuid.UUID) -> Response:
        """Validate payload and persist the review."""
        from rest_framework import serializers as drf_serializers

        class _S(drf_serializers.Serializer):
            rating = drf_serializers.IntegerField(min_value=1, max_value=5)
            highlights = drf_serializers.ListField(
                child=drf_serializers.CharField(max_length=100),
                required=False,
                default=list,
            )
            note = drf_serializers.CharField(max_length=2000, required=False, default="", allow_blank=True)

        ser = _S(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        user_id = uuid.UUID(str(request.user.id))

        if EventReview.objects.filter(event_id=event_id, user_id=user_id).exists():
            return error_response(
                code="ERR_REVIEW_ALREADY_EXISTS",
                message="You have already reviewed this event.",
                http_status=409,
                request=request,
            )

        review = EventReview.objects.create(
            event_id=event_id,
            user_id=user_id,
            rating=d["rating"],
            highlights=d["highlights"],
            note=d["note"],
        )
        return created_response(
            {
                "id": str(review.id),
                "event_id": str(review.event_id),
                "user_id": str(review.user_id),
                "rating": review.rating,
                "highlights": review.highlights,
                "note": review.note,
                "created_at": review.created_at.isoformat(),
            },
            request=request,
        )


class EventReviewSummaryView(APIView):
    """Return average rating and review count for a specific event."""

    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Reviews"],
        summary="Event review summary",
        description="Returns the average rating and total review count for the given event.",
        responses={
            200: OpenApiResponse(description="Summary returned."),
        },
    )
    def get(self, request: Request, event_id: uuid.UUID) -> Response:
        """Aggregate and return the rating summary for the event."""
        from django.db.models import Avg, Count

        result = EventReview.objects.filter(event_id=event_id).aggregate(
            avg_rating=Avg("rating"),
            count=Count("id"),
        )
        return success_response(
            {
                "event_id": str(event_id),
                "average_rating": round(result["avg_rating"], 2) if result["avg_rating"] else None,
                "review_count": result["count"],
            },
            request=request,
        )
