"""Unit tests for Redis-backed capacity counter on the event-service side."""

from __future__ import annotations

import uuid
from datetime import timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

from apps.events.domain.entities import EventEntity
from apps.events.infrastructure.capacity import (
    get_capacity_count,
    init_capacity_counter,
)
from apps.events.tests.unit.fakes import FakeEventRepository, make_event


def _published_event(**kwargs: object) -> EventEntity:
    """Return a published event entity with sensible defaults."""
    from datetime import datetime

    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid.uuid4(),
        organiser_id=uuid.uuid4(),
        title="Redis Test Event",
        description="desc",
        location="Kathmandu",
        start_date=now + timedelta(days=7),
        end_date=now + timedelta(days=8),
        capacity=100,
        registered_count=30,
        status="published",
        visibility="public",
        is_free=True,
        price=Decimal("0.00"),
        created_at=now,
        updated_at=now,
        deleted_at=None,
    )
    defaults.update(kwargs)
    return EventEntity(**defaults)  # type: ignore[arg-type]


class TestInitCapacityCounter:
    """init_capacity_counter sets the Redis key to registered_count."""

    def test_sets_redis_key_to_registered_count(self) -> None:
        """Redis key event_capacity:{id} must be set to registered_count."""
        event = _published_event(registered_count=42)
        mock_redis = MagicMock()

        init_capacity_counter(event=event, redis_client=mock_redis)

        mock_redis.set.assert_called_once_with(f"event_capacity:{event.id}", 42)

    def test_key_name_includes_event_id(self) -> None:
        """Key must include the event UUID to avoid collisions."""
        event_id = uuid.uuid4()
        event = _published_event(id=event_id, registered_count=0)
        mock_redis = MagicMock()

        init_capacity_counter(event=event, redis_client=mock_redis)

        call_args = mock_redis.set.call_args
        assert str(event_id) in call_args[0][0]


class TestGetCapacityCount:
    """get_capacity_count reads from Redis or falls back to DB count."""

    def test_returns_redis_value_when_available(self) -> None:
        """Should parse and return the int stored in Redis."""
        event_id = uuid.uuid4()
        mock_redis = MagicMock()
        mock_redis.get.return_value = b"55"

        count = get_capacity_count(event_id=event_id, redis_client=mock_redis, db_count=10)

        assert count == 55

    def test_falls_back_to_db_count_when_redis_returns_none(self) -> None:
        """When Redis has no key, db_count must be returned."""
        event_id = uuid.uuid4()
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        count = get_capacity_count(event_id=event_id, redis_client=mock_redis, db_count=17)

        assert count == 17

    def test_falls_back_to_db_count_on_redis_exception(self) -> None:
        """Any Redis error must be swallowed and db_count returned."""
        event_id = uuid.uuid4()
        mock_redis = MagicMock()
        mock_redis.get.side_effect = Exception("connection refused")

        count = get_capacity_count(event_id=event_id, redis_client=mock_redis, db_count=99)

        assert count == 99

    def test_reads_correct_key(self) -> None:
        """Must request the key event_capacity:{event_id}."""
        event_id = uuid.uuid4()
        mock_redis = MagicMock()
        mock_redis.get.return_value = b"0"

        get_capacity_count(event_id=event_id, redis_client=mock_redis, db_count=0)

        mock_redis.get.assert_called_once_with(f"event_capacity:{event_id}")


class TestPublishEventInitializesRedis:
    """PublishEventUseCase initialises the Redis capacity counter on publish."""

    def test_publish_calls_init_capacity_counter(self) -> None:
        """After a successful publish, the Redis counter must be initialised."""
        from apps.events.application.use_cases.publish_event import PublishEventUseCase

        event = make_event(status="draft", registered_count=5)
        repo = FakeEventRepository(events=[event])

        mock_redis = MagicMock()

        with patch("apps.events.infrastructure.capacity.init_capacity_counter") as mock_init:
            PublishEventUseCase(event_repo=repo, redis_client=mock_redis).execute(
                event_id=event.id,
                organiser_id=event.organiser_id,
            )

        mock_init.assert_called_once()
        called_event = mock_init.call_args[1]["event"]
        assert called_event.status == "published"
