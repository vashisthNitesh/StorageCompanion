from .base import *

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

SIMPLE_JWT["AUTH_COOKIE_SECURE"] = False

# Console email backend for testing
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# In local dev, allow 'unsafe-eval' for Vite HMR and dev tooling alongside 'wasm-unsafe-eval'
CONTENT_SECURITY_POLICY = CONTENT_SECURITY_POLICY.replace(
    "script-src 'self'",
    "script-src 'self' 'unsafe-eval'",
)
