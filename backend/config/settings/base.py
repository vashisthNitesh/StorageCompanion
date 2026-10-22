from datetime import timedelta
from pathlib import Path
import environ

# Base directory: backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ENVIRONMENT=(str, "dev"),
    SECRET_KEY=(str, "insecure-dev-key-change-in-production"),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    DATABASE_URL=(str, "sqlite:///db.sqlite3"),
    SPACEBYTE_BASE_URL=(str, "https://spacebyte.in/api/v1"),
    SPACEBYTE_ACCESS_TOKEN=(str, ""),
    SPACEBYTE_STORAGE_POOL_LIMIT_BYTES=(int, 1000 * 1024 * 1024 * 1024),  # 1 TB testing allocation
    SPACEBYTE_PARENT_FOLDER_ID=(str, ""),
    DEFAULT_CURRENCY=(str, "INR"),
    # Payments are refused until real Razorpay keys are configured.
    RAZORPAY_KEY_ID=(str, ""),
    RAZORPAY_KEY_SECRET=(str, ""),
    RAZORPAY_WEBHOOK_SECRET=(str, ""),
    GOOGLE_CLIENT_ID=(str, ""),
    # Secret used to derive vault keys for Google sign-in accounts. Defaults to SECRET_KEY;
    # set it explicitly before ever rotating SECRET_KEY or Google users lose their files.
    VAULT_KEY_SECRET=(str, ""),
    # Seller details printed on invoices. Without a GSTIN the invoice is a plain receipt.
    BUSINESS_NAME=(str, "SmartSpace"),
    BUSINESS_ADDRESS=(str, ""),
    BUSINESS_GSTIN=(str, ""),
    BUSINESS_STATE_CODE=(str, ""),
    # Number of reverse proxies in front of Django (Render's edge + nginx) for client-IP throttling.
    NUM_PROXIES=(int, 0),
)

# Read .env if present
env_file = BASE_DIR.parent / ".env"
if not env_file.exists():
    env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ENVIRONMENT = env("ENVIRONMENT")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID")
VAULT_KEY_SECRET = env("VAULT_KEY_SECRET") or SECRET_KEY

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    # Local apps
    "apps.common",
    "apps.accounts",
    "apps.storage",
    "apps.billing",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.common.middleware.ContentSecurityPolicyMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            BASE_DIR.parent / "frontend" / "dist",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database (Supports PostgreSQL / Neon DB / SQLite)
DATABASES = {
    "default": env.db("DATABASE_URL", default="sqlite:///db.sqlite3")
}

# Neon Serverless Postgres auto-configuration
db_host = DATABASES["default"].get("HOST", "")
db_url = env.str("DATABASE_URL", default="")
if "neon.tech" in db_host or "neon.tech" in db_url:
    DATABASES["default"].setdefault("OPTIONS", {})["sslmode"] = "require"
    # Keep connections non-persistent or short-lived for Neon serverless pooler
    DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=0)
else:
    DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)

if DATABASES["default"]["ENGINE"].endswith("sqlite3"):
    # Local development: wait for concurrent upload writes instead of failing with "database is locked".
    DATABASES["default"].setdefault("OPTIONS", {})["timeout"] = 20

# Password validation & Argon2id hasher
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Custom User Model
AUTH_USER_MODEL = "accounts.User"

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files & WhiteNoise
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = []
dist_path = BASE_DIR.parent / "frontend" / "dist"
if (dist_path / "assets").exists():
    STATICFILES_DIRS.append(dist_path / "assets")

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}
WHITENOISE_INDEX_FILE = True
WHITENOISE_ROOT = dist_path if dist_path.exists() else None

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.accounts.authentication.SessionJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.StandardCursorPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    # Upload relay sends one request per 20 MB part, so the per-user budget is generous.
    # Login, Google sign-in, refresh and MFA endpoints add a stricter "auth" scope on top.
    "DEFAULT_THROTTLE_RATES": {
        "anon": "300/hour",
        "user": "20000/day",
        "auth": "10/minute",
        "refresh": "60/minute",
    },
    "NUM_PROXIES": env("NUM_PROXIES") or None,
    "EXCEPTION_HANDLER": "apps.common.exceptions.custom_exception_handler",
}

# SimpleJWT Settings
SIMPLE_JWT = {
    # Access tokens are short-lived; every request also checks the token's session is not revoked.
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    # Cookie settings for refresh token
    "AUTH_COOKIE": "refresh_token",
    "AUTH_COOKIE_DOMAIN": None,
    "AUTH_COOKIE_SECURE": False,  # True in prod
    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_PATH": "/api/v1/auth/",
    "AUTH_COOKIE_SAMESITE": "Strict",
}

# Payments (Razorpay). The placeholder values that older configs shipped with are public,
# so they are treated as "not configured" rather than as real secrets.
_PLACEHOLDER_SECRETS = {"rzp_test_sample", "sample_secret_key", "sample_webhook_secret"}
DEFAULT_CURRENCY = env("DEFAULT_CURRENCY")
RAZORPAY_KEY_ID = "" if env("RAZORPAY_KEY_ID") in _PLACEHOLDER_SECRETS else env("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = "" if env("RAZORPAY_KEY_SECRET") in _PLACEHOLDER_SECRETS else env("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = "" if env("RAZORPAY_WEBHOOK_SECRET") in _PLACEHOLDER_SECRETS else env("RAZORPAY_WEBHOOK_SECRET")

# Invoice seller details
BUSINESS_NAME = env("BUSINESS_NAME")
BUSINESS_ADDRESS = env("BUSINESS_ADDRESS")
BUSINESS_GSTIN = env("BUSINESS_GSTIN")
BUSINESS_STATE_CODE = env("BUSINESS_STATE_CODE")

# SpaceByte Cloud Storage Upstream Integration
SPACEBYTE_BASE_URL = env("SPACEBYTE_BASE_URL")
SPACEBYTE_ACCESS_TOKEN = env("SPACEBYTE_ACCESS_TOKEN")
SPACEBYTE_STORAGE_POOL_LIMIT_BYTES = env("SPACEBYTE_STORAGE_POOL_LIMIT_BYTES")
SPACEBYTE_PARENT_FOLDER_ID = env("SPACEBYTE_PARENT_FOLDER_ID")

# Content-Security-Policy sent by Django responses (nginx sends the same policy for the SPA).
CONTENT_SECURITY_POLICY = "; ".join([
    "default-src 'self'",
    "script-src 'self' 'wasm-unsafe-eval' https://accounts.google.com/gsi/client https://checkout.razorpay.com https://*.razorpay.com",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://accounts.google.com/gsi/style",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: blob: https://*.googleusercontent.com https://*.razorpay.com",
    "connect-src 'self' https://accounts.google.com/gsi/ https://*.razorpay.com",
    "frame-src https://accounts.google.com/gsi/ https://*.razorpay.com",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])
