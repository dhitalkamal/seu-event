"""Unit tests for org-role permission classes."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

ORG_ID = uuid.uuid4()
OTHER_ORG_ID = uuid.uuid4()


def _make_request(org_id: uuid.UUID | None, role: str | None) -> MagicMock:
    """Build a mock request with JWT payload containing org_roles."""
    request = MagicMock()
    if org_id is not None and role is not None:
        request.user.token.payload = {"org_roles": {str(org_id): role}}
    else:
        request.user.token.payload = {"org_roles": {}}
    return request


def _make_view(org_id: uuid.UUID | None = None) -> MagicMock:
    """Build a mock view with optional org_id attribute."""
    view = MagicMock()
    view.org_id = org_id
    view.kwargs = {}
    return view


class TestIsOrgOwner:
    """IsOrgOwner grants access only to the owner role."""

    def test_allows_owner(self) -> None:
        """User with owner role on the org is permitted."""
        from apps.common.permissions import IsOrgOwner

        perm = IsOrgOwner()
        request = _make_request(ORG_ID, "owner")
        view = _make_view(ORG_ID)
        assert perm.has_permission(request, view) is True

    def test_denies_admin(self) -> None:
        """User with admin role is not permitted by IsOrgOwner."""
        from apps.common.permissions import IsOrgOwner

        perm = IsOrgOwner()
        request = _make_request(ORG_ID, "admin")
        view = _make_view(ORG_ID)
        assert perm.has_permission(request, view) is False

    def test_denies_when_no_org_id(self) -> None:
        """Request with no org_id context is denied."""
        from apps.common.permissions import IsOrgOwner

        perm = IsOrgOwner()
        request = _make_request(ORG_ID, "owner")
        view = _make_view(None)
        assert perm.has_permission(request, view) is False


class TestIsOrgAdmin:
    """IsOrgAdmin grants access to owner and admin roles."""

    def test_allows_owner(self) -> None:
        """Owner role satisfies admin-level permission."""
        from apps.common.permissions import IsOrgAdmin

        perm = IsOrgAdmin()
        request = _make_request(ORG_ID, "owner")
        view = _make_view(ORG_ID)
        assert perm.has_permission(request, view) is True

    def test_allows_admin(self) -> None:
        """Admin role satisfies admin-level permission."""
        from apps.common.permissions import IsOrgAdmin

        perm = IsOrgAdmin()
        request = _make_request(ORG_ID, "admin")
        view = _make_view(ORG_ID)
        assert perm.has_permission(request, view) is True

    def test_denies_manager(self) -> None:
        """Manager role does not satisfy admin-level permission."""
        from apps.common.permissions import IsOrgAdmin

        perm = IsOrgAdmin()
        request = _make_request(ORG_ID, "manager")
        view = _make_view(ORG_ID)
        assert perm.has_permission(request, view) is False


class TestIsOrgManager:
    """IsOrgManager grants access to owner, admin, and manager roles."""

    def test_allows_manager(self) -> None:
        """Manager role satisfies manager-level permission."""
        from apps.common.permissions import IsOrgManager

        perm = IsOrgManager()
        request = _make_request(ORG_ID, "manager")
        view = _make_view(ORG_ID)
        assert perm.has_permission(request, view) is True

    def test_denies_member(self) -> None:
        """Member role does not satisfy manager-level permission."""
        from apps.common.permissions import IsOrgManager

        perm = IsOrgManager()
        request = _make_request(ORG_ID, "member")
        view = _make_view(ORG_ID)
        assert perm.has_permission(request, view) is False


class TestIsOrgMember:
    """IsOrgMember grants access to any recognised role in the org."""

    def test_allows_member(self) -> None:
        """Member role satisfies member-level permission."""
        from apps.common.permissions import IsOrgMember

        perm = IsOrgMember()
        request = _make_request(ORG_ID, "member")
        view = _make_view(ORG_ID)
        assert perm.has_permission(request, view) is True

    def test_denies_non_member(self) -> None:
        """User with no role in the org is denied."""
        from apps.common.permissions import IsOrgMember

        perm = IsOrgMember()
        request = _make_request(OTHER_ORG_ID, "member")
        view = _make_view(ORG_ID)
        assert perm.has_permission(request, view) is False

    def test_denies_when_no_org_id(self) -> None:
        """Request with no org_id context is denied."""
        from apps.common.permissions import IsOrgMember

        perm = IsOrgMember()
        request = _make_request(ORG_ID, "member")
        view = _make_view(None)
        assert perm.has_permission(request, view) is False
