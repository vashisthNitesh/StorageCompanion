from rest_framework_simplejwt.authentication import JWTAuthentication


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
        # NOTE: ?token= / ?access_token= query parameters are intentionally NOT accepted any more:
        # URLs end up in proxy/access logs, browser history and Referer headers, leaking a
        # 24-hour bearer token. The frontend never used them.

        if raw_token is None:
            return None

        validated_token = self.get_validated_token(raw_token)
        return self.get_user(validated_token), validated_token
