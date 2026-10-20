from .base import *

DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", ".onrender.com", "smartspacedata.com", ".smartspacedata.com"],
)
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["https://*.onrender.com", "https://smartspacedata.com", "https://*.smartspacedata.com"],
)

# Cookie security (secure on HTTPS)
SIMPLE_JWT["AUTH_COOKIE_SECURE"] = env.bool("COOKIE_SECURE", default=True)
SESSION_COOKIE_SECURE = env.bool("COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = env.bool("COOKIE_SECURE", default=True)

# Security Headers (Content-Security-Policy is set by apps.common.middleware and nginx)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 30)
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
