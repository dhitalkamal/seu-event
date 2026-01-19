"""Unit tests for EventPublisher."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch


def test_publish_event_updated_sends_correct_routing_key() -> None:
    """publish_event_updated sends a message with routing_key event.updated."""
    with patch("apps.events.infrastructure.event_publisher.pika") as mock_pika:
        mock_conn = MagicMock()
        mock_channel = MagicMock()
        mock_pika.BlockingConnection.return_value = mock_conn
        mock_conn.channel.return_value = mock_channel

        from apps.events.infrastructure.event_publisher import EventPublisher

        publisher = EventPublisher()
        publisher.publish_event_updated(
            event_id=uuid.uuid4(),
            organiser_id=uuid.uuid4(),
            title="My Conference",
        )

        mock_channel.basic_publish.assert_called_once()
        kwargs = mock_channel.basic_publish.call_args.kwargs
        assert kwargs["routing_key"] == "event.updated"


def test_publish_event_updated_includes_all_fields() -> None:
    """publish_event_updated payload contains event_id, organiser_id, and title."""
    import json

    with patch("apps.events.infrastructure.event_publisher.pika") as mock_pika:
        mock_conn = MagicMock()
        mock_channel = MagicMock()
        mock_pika.BlockingConnection.return_value = mock_conn
        mock_conn.channel.return_value = mock_channel

        from apps.events.infrastructure.event_publisher import EventPublisher

        publisher = EventPublisher()
        event_id = uuid.uuid4()
        organiser_id = uuid.uuid4()
        publisher.publish_event_updated(
            event_id=event_id,
            organiser_id=organiser_id,
            title="My Conference",
        )

        body = mock_channel.basic_publish.call_args.kwargs["body"]
        payload = json.loads(body)
        assert payload["event_id"] == str(event_id)
        assert payload["organiser_id"] == str(organiser_id)
        assert payload["title"] == "My Conference"


def test_publish_event_published_sends_correct_routing_key() -> None:
    """publish_event_published sends a message with routing_key event.published."""
    with patch("apps.events.infrastructure.event_publisher.pika") as mock_pika:
        mock_conn = MagicMock()
        mock_channel = MagicMock()
        mock_pika.BlockingConnection.return_value = mock_conn
        mock_conn.channel.return_value = mock_channel

        from apps.events.infrastructure.event_publisher import EventPublisher

        publisher = EventPublisher()
        publisher.publish_event_published(
            event_id=uuid.uuid4(),
            organiser_id=uuid.uuid4(),
            title="My Conference",
        )

        mock_channel.basic_publish.assert_called_once()
        kwargs = mock_channel.basic_publish.call_args.kwargs
        assert kwargs["routing_key"] == "event.published"


def test_publish_event_cancelled_sends_correct_routing_key() -> None:
    """publish_event_cancelled sends a message with routing_key event.cancelled."""
    with patch("apps.events.infrastructure.event_publisher.pika") as mock_pika:
        mock_conn = MagicMock()
        mock_channel = MagicMock()
        mock_pika.BlockingConnection.return_value = mock_conn
        mock_conn.channel.return_value = mock_channel

        from apps.events.infrastructure.event_publisher import EventPublisher

        publisher = EventPublisher()
        publisher.publish_event_cancelled(
            event_id=uuid.uuid4(),
            organiser_id=uuid.uuid4(),
            title="My Conference",
        )

        mock_channel.basic_publish.assert_called_once()
        kwargs = mock_channel.basic_publish.call_args.kwargs
        assert kwargs["routing_key"] == "event.cancelled"
