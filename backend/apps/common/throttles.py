"""
Rate limits keyed on what's being protected rather than only the IP address.

Many people share one public IP (mobile carrier NAT, offices, colleges), so per-IP limits are
generous anti-flood backstops; tight limits apply per account (sign-in) or per signed-in device
(token refresh). Accounts are also locked for 15 minutes after repeated failed sign-ins
(apps.accounts.services.ensure_not_locked_out).
"""
import base64
import hashlib
import json

from django.conf import settings
from rest_framework.throttling import (
    AnonRateThrottle,
    ScopedRateThrottle,
    SimpleRateThrottle,
    UserRateThrottle,
)

from apps.common.net import get_client_ip


class ClientIPMixin:
    def get_ident(self, request):
        return get_client_ip(request) or "unknown"


class AnonThrottle(ClientIPMixin, AnonRateThrottle):
    pass


class UserThrottle(ClientIPMixin, UserRateThrottle):
    pass


class ScopedIPThrottle(ClientIPMixin, ScopedRateThrottle):
    """Per-IP limit for the view's `throttle_scope`."""


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class LoginAccountThrottle(SimpleRateThrottle):
    """Sign-in attempts per account (email), whichever IP they come from."""

    scope = "login_account"

    def get_cache_key(self, request, view):
        email = str(request.data.get("email", "") if hasattr(request.data, "get") else "").strip().lower()
        if not email:
            return None
        return self.cache_format % {"scope": self.scope, "ident": _digest(email)}


class PasswordResetEmailThrottle(SimpleRateThrottle):
    """Password reset emails per address, whichever IP asks."""

    scope = "password_reset_email"

    def get_cache_key(self, request, view):
        email = str(request.data.get("email", "") if hasattr(request.data, "get") else "").strip().lower()
        if not email:
            return None
        return self.cache_format % {"scope": self.scope, "ident": _digest(email)}


class RefreshSessionThrottle(ClientIPMixin, SimpleRateThrottle):
    """
    Token refreshes per signed-in device. The session id ("sid") is read from the refresh cookie
    without verifying it: a forged value only gets its own bucket, and the refresh itself still
    fails signature checks. Requests without a usable cookie fall back to the client IP.
    """

    scope = "refresh"

    def get_cache_key(self, request, view):
        token = request.COOKIES.get(settings.SIMPLE_JWT["AUTH_COOKIE"], "")
        sid = ""
        try:
            payload = token.split(".")[1]
            sid = str(json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4))).get("sid", ""))
        except (IndexError, ValueError, AttributeError):
            pass
        ident = f"sid:{_digest(sid)}" if sid else f"ip:{self.get_ident(request)}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


class RefreshIPThrottle(ClientIPMixin, SimpleRateThrottle):
    """Generous per-IP backstop for token refreshes."""

    scope = "refresh_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
