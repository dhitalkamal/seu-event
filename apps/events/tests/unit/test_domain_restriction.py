"""Unit tests for domain-restricted event visibility."""

from __future__ import annotations

from apps.events.application.use_cases.list_events import ListEventsUseCase
from apps.events.tests.unit.fakes import FakeEventRepository, make_event


def _pub(**kwargs) -> object:
    """Shorthand for a published public event."""
    return make_event(status="published", visibility="public", **kwargs)


def test_unrestricted_events_visible_to_all():
    """Events with no allowed_domains are visible regardless of email domain."""
    event = _pub(allowed_domains=[])
    repo = FakeEventRepository([event])
    results = ListEventsUseCase(repo).execute()
    assert len(results) == 1


def test_unrestricted_events_visible_when_no_email():
    """Unauthenticated user (no email) still sees unrestricted events."""
    event = _pub(allowed_domains=[])
    repo = FakeEventRepository([event])
    results = ListEventsUseCase(repo).execute(user_email_domain=None)
    assert len(results) == 1


def test_domain_restricted_event_hidden_from_unauthenticated():
    """A domain-restricted event is hidden when user_email_domain is None."""
    event = _pub(allowed_domains=["example.edu"])
    repo = FakeEventRepository([event])
    results = ListEventsUseCase(repo).execute(user_email_domain=None)
    assert results == []


def test_domain_restricted_event_hidden_from_wrong_domain():
    """A domain-restricted event is hidden from users with a non-matching domain."""
    event = _pub(allowed_domains=["example.edu"])
    repo = FakeEventRepository([event])
    results = ListEventsUseCase(repo).execute(user_email_domain="other.com")
    assert results == []


def test_domain_restricted_event_visible_to_matching_domain():
    """A domain-restricted event is visible to users whose email domain matches."""
    event = _pub(allowed_domains=["example.edu"])
    repo = FakeEventRepository([event])
    results = ListEventsUseCase(repo).execute(user_email_domain="example.edu")
    assert len(results) == 1
    assert results[0].id == event.id


def test_multiple_allowed_domains_any_match_grants_access():
    """If allowed_domains has multiple entries, any match grants visibility."""
    event = _pub(allowed_domains=["college.edu", "company.com"])
    repo = FakeEventRepository([event])
    assert len(ListEventsUseCase(repo).execute(user_email_domain="company.com")) == 1
    assert len(ListEventsUseCase(repo).execute(user_email_domain="college.edu")) == 1
    assert len(ListEventsUseCase(repo).execute(user_email_domain="random.org")) == 0


def test_domain_check_is_case_insensitive():
    """Domain comparison is case-insensitive."""
    event = _pub(allowed_domains=["Example.EDU"])
    repo = FakeEventRepository([event])
    results = ListEventsUseCase(repo).execute(user_email_domain="example.edu")
    assert len(results) == 1


def test_mixed_restricted_and_unrestricted():
    """List only includes unrestricted + domain-matching restricted events."""
    open_event = _pub(allowed_domains=[])
    restricted_match = _pub(allowed_domains=["uni.edu"])
    restricted_no_match = _pub(allowed_domains=["corp.com"])

    repo = FakeEventRepository([open_event, restricted_match, restricted_no_match])
    results = ListEventsUseCase(repo).execute(user_email_domain="uni.edu")
    ids = {r.id for r in results}
    assert open_event.id in ids
    assert restricted_match.id in ids
    assert restricted_no_match.id not in ids
