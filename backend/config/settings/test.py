"""Settings for the automated test suite.

Always uses an in-memory SQLite database and a disabled SpaceByte client so a
test run can never touch the live Postgres database or upstream storage,
whatever is in .env.
"""
from .base import *  # noqa: F401,F403

DEBUG = True
ENVIRONMENT = "test"
SECRET_KEY = "test-only-secret-key-not-used-anywhere-else"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
SPACEBYTE_ACCESS_TOKEN = ""
GOOGLE_CLIENT_ID = "test-google-client-id.apps.googleusercontent.com"
RAZORPAY_KEY_ID = "rzp_test_unit"
RAZORPAY_KEY_SECRET = "unit_test_key_secret"
RAZORPAY_WEBHOOK_SECRET = "unit_test_webhook_secret"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
SIMPLE_JWT = {**SIMPLE_JWT, "SIGNING_KEY": SECRET_KEY}
