"""RabbitMQ event publisher for event domain events."""

from __future__ import annotations

import json
import logging
import uuid

import pika
from django.conf import settings

logger = logging.getLogger(__name__)

# exchange name matches the rest of the sansaar platform
_EXCHANGE = "sansaar"
_EXCHANGE_TYPE = "topic"


class EventPublisher:
    """Publishes event.* domain events to the sansaar topic exchange."""

    def _publish(self, routing_key: str, payload: dict) -> None:
        """
        Open a fresh connection, declare the exchange, publish the message, then close.

        Fresh connection per publish -- acceptable for low-frequency lifecycle events.
        If RabbitMQ is unavailable the failure is logged and swallowed so the
        caller's DB transaction is not rolled back.

        @param routing_key - the topic routing key, e.g. "event.updated"
        @param payload     - JSON-serialisable dict sent as the message body
        """
        try:
            params = pika.URLParameters(settings.RABBITMQ_URL)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(
                exchange=_EXCHANGE,
                exchange_type=_EXCHANGE_TYPE,
                durable=True,
            )
            channel.basic_publish(
                exchange=_EXCHANGE,
                routing_key=routing_key,
                body=json.dumps(payload),
                properties=pika.BasicProperties(
                    content_type="application/json",
                    delivery_mode=pika.DeliveryMode.Persistent,
                ),
            )
            connection.close()
        except Exception:
            # ! do not block the caller -- RabbitMQ is observability infrastructure,
            # not part of the primary write path
            logger.warning(
                "Failed to publish %s to RabbitMQ.",
                routing_key,
                exc_info=True,
            )

    def publish_event_updated(
        self,
        *,
        event_id: uuid.UUID,
        organiser_id: uuid.UUID,
        title: str,
    ) -> None:
        """
        Publish an event.updated event after an event is partially updated.

        @param event_id     - the updated event's UUID
        @param organiser_id - UUID of the event organiser
        @param title        - current title of the event after the update
        """
        self._publish(
            "event.updated",
            {
                "event_id": str(event_id),
                "organiser_id": str(organiser_id),
                "title": title,
            },
        )

    def publish_event_published(
        self,
        *,
        event_id: uuid.UUID,
        organiser_id: uuid.UUID,
        title: str,
    ) -> None:
        """
        Publish an event.published event after a draft event goes live.

        @param event_id     - the published event's UUID
        @param organiser_id - UUID of the event organiser
        @param title        - title of the newly published event
        """
        self._publish(
            "event.published",
            {
                "event_id": str(event_id),
                "organiser_id": str(organiser_id),
                "title": title,
            },
        )

    def publish_event_cancelled(
        self,
        *,
        event_id: uuid.UUID,
        organiser_id: uuid.UUID,
        title: str,
    ) -> None:
        """
        Publish an event.cancelled event after an event is soft-deleted.

        @param event_id     - the cancelled event's UUID
        @param organiser_id - UUID of the event organiser
        @param title        - title of the cancelled event
        """
        self._publish(
            "event.cancelled",
            {
                "event_id": str(event_id),
                "organiser_id": str(organiser_id),
                "title": title,
            },
        )
