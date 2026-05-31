"""Management command: event service RabbitMQ event consumer."""

from __future__ import annotations

import json
import logging
import os
import uuid

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)

_QUEUE = "events.participation"
_ROUTING_KEY = "participation.registration.#"


class Command(BaseCommand):
    """
    Listen for participation events and update registered_count on events.

    Handles:
    - participation.registration.created -> increment registered_count
    - participation.registration.cancelled -> decrement registered_count
    """

    help = "Event service RabbitMQ consumer."

    def handle(self, *args: object, **options: object) -> None:
        """Connect to RabbitMQ and consume participation events."""
        import pika

        rabbitmq_url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
        self.stdout.write("Event consumer started.")
        try:
            params = pika.URLParameters(rabbitmq_url)
            connection = pika.BlockingConnection(params)
            channel = connection.channel()
            channel.exchange_declare(exchange="sansaar", exchange_type="topic", durable=True)
            channel.queue_declare(queue=_QUEUE, durable=True)
            channel.queue_bind(queue=_QUEUE, exchange="sansaar", routing_key=_ROUTING_KEY)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=_QUEUE, on_message_callback=self._handle)
            channel.start_consuming()
        except KeyboardInterrupt:
            self.stdout.write("Event consumer stopped.")
        except Exception:
            logger.exception("Event consumer error.")

    @staticmethod
    def _handle(channel: object, method: object, props: object, body: bytes) -> None:
        """Update registered_count based on the participation event."""
        import pika.spec

        assert isinstance(method, pika.spec.Basic.Deliver)
        try:
            payload = json.loads(body)
            event_id = payload.get("event_id")
            routing_key: str = method.routing_key
            if not event_id:
                channel.basic_ack(delivery_tag=method.delivery_tag)
                return

            from apps.events.infrastructure.repositories import DjangoEventRepository

            repo = DjangoEventRepository()
            try:
                event = repo.get_by_id(uuid.UUID(event_id))
                if routing_key.endswith(".created"):
                    event.registered_count = max(0, event.registered_count + 1)
                elif routing_key.endswith(".cancelled"):
                    event.registered_count = max(0, event.registered_count - 1)
                repo.update(event)
                logger.info("Updated registered_count for event %s via %s", event_id, routing_key)
            except Exception:
                logger.warning("Could not update event %s.", event_id, exc_info=True)

            channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception:
            logger.exception("Event consumer failed to process message.")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
