"""Publishes audit events to the centralized iam_audit_log via RabbitMQ."""

from __future__ import annotations

import json
import logging
import uuid

import pika
from django.conf import settings
from rest_framework.request import Request

logger = logging.getLogger(__name__)

_EXCHANGE = "sansaar"


def _get_ip(request: Request) -> str | None:
    """Extract client IP, respecting X-Forwarded-For."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def publish_audit(
    request: Request,
    user_id: uuid.UUID,
    event_type: str,
    metadata: dict | None = None,
) -> None:
    """Publish an audit event to the sansaar exchange on routing key audit.log.

    Failures are logged and swallowed so the caller's response is never blocked.
    """
    payload = {
        "user_id": str(user_id),
        "event_type": event_type,
        "ip_address": _get_ip(request),
        "user_agent": request.META.get("HTTP_USER_AGENT"),
        "metadata": metadata or {},
    }
    try:
        params = pika.URLParameters(settings.RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.exchange_declare(exchange=_EXCHANGE, exchange_type="topic", durable=True)
        channel.basic_publish(
            exchange=_EXCHANGE,
            routing_key="audit.log",
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=pika.DeliveryMode.Persistent,
            ),
        )
        connection.close()
    except Exception:
        logger.warning("Failed to publish audit event %s.", event_type, exc_info=True)
