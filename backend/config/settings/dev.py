from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "web", "*"]

SIMPLE_JWT["AUTH_COOKIE_SECURE"] = False

# Console email backend for testing
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
