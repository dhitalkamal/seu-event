"""Unit tests for the cross-service audit publisher."""

from __future__ import annotations

import json
import uuid
from unittest.mock import MagicMock, patch


def test_publish_audit_sends_to_audit_log_routing_key() -> None:
    """publish_audit sends a message with routing_key audit.log."""
    with patch("apps.events.infrastructure.audit_publisher.pika") as mock_pika:
        mock_conn = MagicMock()
        mock_channel = MagicMock()
        mock_pika.BlockingConnection.return_value = mock_conn
        mock_conn.channel.return_value = mock_channel

        from apps.events.infrastructure.audit_publisher import publish_audit

        request = MagicMock()
        request.META = {
            "HTTP_X_FORWARDED_FOR": "1.2.3.4",
            "HTTP_USER_AGENT": "TestAgent/1.0",
        }

        publish_audit(
            request=request,
            user_id=uuid.uuid4(),
            event_type="event.created",
            metadata={"title": "My Event"},
        )

        mock_channel.basic_publish.assert_called_once()
        kwargs = mock_channel.basic_publish.call_args.kwargs
        assert kwargs["routing_key"] == "audit.log"


def test_publish_audit_payload_contains_all_fields() -> None:
    """publish_audit payload contains user_id, event_type, ip, user_agent, metadata."""
    with patch("apps.events.infrastructure.audit_publisher.pika") as mock_pika:
        mock_conn = MagicMock()
        mock_channel = MagicMock()
        mock_pika.BlockingConnection.return_value = mock_conn
        mock_conn.channel.return_value = mock_channel

        from apps.events.infrastructure.audit_publisher import publish_audit

        request = MagicMock()
        request.META = {
            "HTTP_X_FORWARDED_FOR": "10.0.0.1, 192.168.1.1",
            "HTTP_USER_AGENT": "TestBrowser/2.0",
        }

        uid = uuid.uuid4()
        publish_audit(
            request=request,
            user_id=uid,
            event_type="event.created",
            metadata={"title": "Conference"},
        )

        body = mock_channel.basic_publish.call_args.kwargs["body"]
        payload = json.loads(body)
        assert payload["user_id"] == str(uid)
        assert payload["event_type"] == "event.created"
        assert payload["ip_address"] == "10.0.0.1"
        assert payload["user_agent"] == "TestBrowser/2.0"
        assert payload["metadata"] == {"title": "Conference"}


def test_publish_audit_swallows_connection_errors() -> None:
    """publish_audit does not raise when RabbitMQ is unavailable."""
    with patch("apps.events.infrastructure.audit_publisher.pika") as mock_pika:
        mock_pika.BlockingConnection.side_effect = ConnectionError("no rabbit")

        from apps.events.infrastructure.audit_publisher import publish_audit

        request = MagicMock()
        request.META = {}

        publish_audit(
            request=request,
            user_id=uuid.uuid4(),
            event_type="event.created",
        )
