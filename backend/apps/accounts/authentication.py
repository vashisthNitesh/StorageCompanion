from django.conf import settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed


class CookieJWTAuthentication(JWTAuthentication):
    """
    Standard JWT authentication that reads the Bearer token from the Authorization header.
    Can also fall back to checking query parameters (?token=... or ?access_token=...)
    or cookies if provided (e.g. for media streaming, audio/video elements, and previews).
    """
    def authenticate(self, request):
        header = self.get_header(request)
        raw_token = None
        if header is not None:
            raw_token = self.get_raw_token(header)
        elif "token" in request.query_params:
            raw_token = request.query_params["token"].encode("utf-8")
        elif "access_token" in request.query_params:
            raw_token = request.query_params["access_token"].encode("utf-8")

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
