"""Elasticsearch-backed implementation of IEventSearchIndex."""

from __future__ import annotations

import logging
import uuid

from django.conf import settings
from elasticsearch import Elasticsearch, NotFoundError

from apps.events.domain.entities import EventEntity
from apps.events.domain.repositories import IEventSearchIndex

logger = logging.getLogger(__name__)


def _get_client() -> Elasticsearch:
    """Build a lazily-initialised Elasticsearch client from settings."""
    return Elasticsearch(settings.ELASTICSEARCH_URL)


def _event_doc(entity: EventEntity) -> dict:
    """Serialise an EventEntity to the Elasticsearch document shape."""
    return {
        "id": str(entity.id),
        "organiser_id": str(entity.organiser_id),
        "title": entity.title,
        "description": entity.description,
        "status": entity.status,
        "is_free": entity.is_free,
        "ticket_price": str(entity.price),
        "capacity": entity.capacity,
        "location": entity.location,
        "online_url": entity.online_url,
        "start_date": entity.start_date.isoformat() if entity.start_date else None,
        "end_date": entity.end_date.isoformat() if entity.end_date else None,
        "category_id": str(entity.category_id) if entity.category_id else None,
        "tag_ids": [str(t) for t in (entity.tag_ids or [])],
        "allowed_domains": entity.allowed_domains or [],
        "cover_image_url": entity.cover_image,
        "registration_count": entity.registered_count,
        "created_at": entity.created_at.isoformat(),
        "updated_at": entity.updated_at.isoformat(),
    }


class ElasticsearchEventIndex(IEventSearchIndex):
    """Indexes and removes events from Elasticsearch on lifecycle transitions."""

    def __init__(self, client: Elasticsearch | None = None) -> None:
        self._client = client or _get_client()
        self._index = settings.ELASTICSEARCH_EVENTS_INDEX

    def index_event(self, entity: EventEntity) -> None:
        """Upsert the event document into the events index."""
        try:
            self._client.index(
                index=self._index,
                id=str(entity.id),
                document=_event_doc(entity),
            )
        except Exception as exc:
            # Log and continue; indexing failure must not break the publish flow.
            logger.warning("Elasticsearch index_event failed for %s: %s", entity.id, exc)

    def delete_event(self, event_id: uuid.UUID) -> None:
        """Remove the event document from the events index."""
        try:
            self._client.delete(index=self._index, id=str(event_id))
        except NotFoundError:
            pass
        except Exception as exc:
            logger.warning("Elasticsearch delete_event failed for %s: %s", event_id, exc)
