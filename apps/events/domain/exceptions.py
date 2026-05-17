"""Domain errors raised by events use cases and never swallowed silently."""

from __future__ import annotations

from apps.common.api.exceptions import DomainError


class EventNotFoundError(DomainError):
    """No event matches the given identifier."""

    http_status = 404
    code = "ERR_EVENT_NOT_FOUND"


class EventNotOwnedError(DomainError):
    """The requesting user is not the event organiser."""

    http_status = 403
    code = "ERR_EVENT_NOT_OWNED"


class InvalidEventStatusTransitionError(DomainError):
    """The requested status change is not permitted by the state machine."""

    http_status = 422
    code = "ERR_EVENT_INVALID_STATUS_TRANSITION"


class EventDateError(DomainError):
    """The supplied dates are logically invalid."""

    http_status = 422
    code = "ERR_EVENT_INVALID_DATES"
