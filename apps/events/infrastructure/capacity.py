"""Redis-backed capacity counter for published events."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from apps.events.domain.entities import EventEntity

logger = logging.getLogger(__name__)

_KEY_PREFIX = "event_capacity"


class _RedisClient(Protocol):
    """Minimal Redis interface used by this module (subset of redis.Redis)."""

    def set(self, name: str, value: int) -> None: ...
    def get(self, name: str) -> bytes | None: ...
    def incr(self, name: str) -> int: ...
    def decr(self, name: str) -> int: ...


def _key(event_id: uuid.UUID) -> str:
    """Return the Redis key for the given event's capacity counter."""
    return f"{_KEY_PREFIX}:{event_id}"


def init_capacity_counter(*, event: "EventEntity", redis_client: _RedisClient) -> None:
    """
    Set the Redis capacity counter for an event to its current registered_count.

    Called when an event is published to seed the fast-path counter.

    @param event - the published event entity
    @param redis_client - a Redis connection or compatible client
    """
    redis_client.set(_key(event.id), event.registered_count)


def get_capacity_count(
    *,
    event_id: uuid.UUID,
    redis_client: _RedisClient,
    db_count: int,
) -> int:
    """
    Return the current registered count from Redis, falling back to db_count.

    Falls back silently on any Redis error or missing key so the caller is
    never blocked by a Redis outage.

    @param event_id - the event whose counter to read
    @param redis_client - a Redis connection or compatible client
    @param db_count - authoritative DB count used as fallback
    @returns current registered count as an integer
    """
    try:
        raw = redis_client.get(_key(event_id))
        if raw is None:
            return db_count
        return int(raw)
    except Exception:
        logger.warning("Redis unavailable for event_capacity:%s, falling back to DB", event_id)
        return db_count


def increment_capacity(*, event_id: uuid.UUID, redis_client: _RedisClient) -> int | None:
    """
    Atomically increment the capacity counter for the given event.

    @param event_id - the event to increment
    @param redis_client - a Redis connection or compatible client
    @returns the new count, or None if Redis is unavailable
    """
    try:
        return redis_client.incr(_key(event_id))
    except Exception:
        logger.warning("Redis unavailable for INCR event_capacity:%s", event_id)
        return None


def decrement_capacity(*, event_id: uuid.UUID, redis_client: _RedisClient) -> int | None:
    """
    Atomically decrement the capacity counter for the given event.

    @param event_id - the event to decrement
    @param redis_client - a Redis connection or compatible client
    @returns the new count, or None if Redis is unavailable
    """
    try:
        return redis_client.decr(_key(event_id))
    except Exception:
        logger.warning("Redis unavailable for DECR event_capacity:%s", event_id)
        return None
