"""Custom DRF permission classes for role-based access control."""

from __future__ import annotations

from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsSuperAdminFromAllowedIP(BasePermission):
    """
    Allow only staff users whose request originates from a whitelisted IP.

    Reads SUPERADMIN_IP_WHITELIST from settings (list of strings).
    If the setting is absent or empty, no IPs are permitted.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Return True when the user is staff and the remote IP is whitelisted."""
        if not request.user or not request.user.is_staff:  # type: ignore[union-attr]
            return False
        whitelist: list[str] = getattr(settings, "SUPERADMIN_IP_WHITELIST", [])
        if not whitelist:
            return False
        # x-forwarded-for may be set by a load balancer; fall back to REMOTE_ADDR
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.META.get("REMOTE_ADDR", "")
        return client_ip in whitelist


class IsOrgRole(BasePermission):
    """
    Base permission that checks a user's role within a specific organisation.

    Subclasses define allowed_roles. The org_id is resolved from the view
    or request in the following priority order:
      1. view.org_id attribute
      2. view.kwargs["org_id"]
      3. view.kwargs["organisation_id"]
      4. request.data["organisation_id"]
      5. request.query_params["organisation_id"]
    """

    allowed_roles: list[str] = []

    def _extract_org_id(self, request: Request, view: APIView) -> str | None:
        """Return the organisation_id string from context, or None when absent."""
        # attribute set directly on the view class
        attr = getattr(view, "org_id", None)
        if attr is not None:
            return str(attr)
        # url kwargs
        kwargs: dict = getattr(view, "kwargs", {}) or {}
        if "org_id" in kwargs:
            return str(kwargs["org_id"])
        if "organisation_id" in kwargs:
            return str(kwargs["organisation_id"])
        # request body - only safe to read when the parser has run
        try:
            body_val = request.data.get("organisation_id")
            if body_val is not None:
                return str(body_val)
        except Exception:  # noqa: BLE001 - guard against unparsed body
            pass
        # query params
        qp = request.query_params.get("organisation_id")
        if qp is not None:
            return str(qp)
        return None

    def _get_org_roles(self, request: Request) -> dict[str, str]:
        """
        Extract the org_roles dict from the JWT payload.

        Falls back to request.user.org_roles for authentication backends
        that materialise roles onto the user object instead of the token.
        """
        try:
            payload: dict = request.user.token.payload  # type: ignore[union-attr]
            return payload.get("org_roles", {})
        except AttributeError:
            pass
        return getattr(request.user, "org_roles", {}) or {}

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Return True when the user holds one of the allowed_roles in the target org."""
        org_id = self._extract_org_id(request, view)
        if org_id is None:
            return False
        org_roles = self._get_org_roles(request)
        user_role = org_roles.get(str(org_id))
        return user_role in self.allowed_roles


class IsOrgOwner(IsOrgRole):
    """Allow only the organisation owner."""

    allowed_roles = ["owner"]


class IsOrgAdmin(IsOrgRole):
    """Allow organisation owners and admins."""

    allowed_roles = ["owner", "admin"]


class IsOrgManager(IsOrgRole):
    """Allow organisation owners, admins, and managers."""

    allowed_roles = ["owner", "admin", "manager"]


class IsOrgMember(IsOrgRole):
    """Allow any recognised organisation member (owner, admin, manager, or member)."""

    allowed_roles = ["owner", "admin", "manager", "member"]
