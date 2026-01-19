"""Unit tests: publish event triggers Elasticsearch indexing."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from apps.events.application.use_cases.publish_event import PublishEventUseCase
from apps.events.tests.unit.fakes import FakeEventRepository, FakeEventSearchIndex, make_event


def _future(days: int = 7) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


def test_publish_indexes_event():
    """Publishing a draft event calls index_event on the search index."""
    organiser_id = uuid.uuid4()
    event = make_event(organiser_id=organiser_id, status="draft", start_date=_future(7))
    repo = FakeEventRepository([event])
    index = FakeEventSearchIndex()

    PublishEventUseCase(repo, search_index=index).execute(event_id=event.id, organiser_id=organiser_id)

    assert len(index.indexed) == 1
    assert index.indexed[0].id == event.id
    assert index.indexed[0].status == "published"


def test_publish_without_index_still_works():
    """PublishEventUseCase works without a search index (backward compatible)."""
    organiser_id = uuid.uuid4()
    event = make_event(organiser_id=organiser_id, status="draft", start_date=_future(7))
    repo = FakeEventRepository([event])

    result = PublishEventUseCase(repo).execute(event_id=event.id, organiser_id=organiser_id)

    assert result.status == "published"
