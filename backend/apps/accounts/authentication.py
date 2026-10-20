from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from apps.accounts.models import Session


class SessionJWTAuthentication(JWTAuthentication):
    """
    Bearer-token JWT authentication that also requires the token's session ("sid" claim)
    to exist and not be revoked, so revoking a session or logging out signs that device
    out immediately instead of when its access token expires.

    Tokens are only accepted in the Authorization header, never in the URL.
    """

    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        session_id = validated_token.get("sid")
        if not session_id:
            raise AuthenticationFailed("Session expired. Please sign in again.", code="session_missing")
        session = Session.objects.filter(id=session_id, user=user).only("id", "revoked_at").first()
        if session is None or session.revoked_at is not None:
            raise AuthenticationFailed("This session has been signed out.", code="session_revoked")
        return user
