import os
from datetime import timedelta
from pathlib import Path
import environ

# Base directory: backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ENVIRONMENT=(str, "dev"),
    SECRET_KEY=(str, "insecure-dev-key-change-in-production"),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1", "web", ".onrender.com", "*"]),
    DATABASE_URL=(str, "sqlite:///db.sqlite3"),
    REDIS_URL=(str, "redis://localhost:6379/0"),
    CELERY_BROKER_URL=(str, "redis://localhost:6379/0"),
    CELERY_RESULT_BACKEND=(str, "redis://localhost:6379/0"),
    S3_ENDPOINT_URL=(str, "http://localhost:9000"),
    S3_ACCESS_KEY_ID=(str, "minioadmin"),
    S3_SECRET_ACCESS_KEY=(str, "minioadmin"),
    S3_BUCKET_NAME=(str, "speedcloud-files"),
    S3_REGION_NAME=(str, "auto"),
    PRESIGNED_URL_TTL=(int, 900),  # 15 minutes max
    SPACEBYTE_BASE_URL=(str, "https://spacebyte.in/api/v1"),
    SPACEBYTE_ACCESS_TOKEN=(str, ""),
    SPACEBYTE_STORAGE_POOL_LIMIT_BYTES=(int, 1000 * 1024 * 1024 * 1024),  # 1 TB testing allocation
    SPACEBYTE_PARENT_FOLDER_ID=(str, ""),
    PAYMENT_PROVIDER=(str, "razorpay"),
    DEFAULT_CURRENCY=(str, "INR"),
    RAZORPAY_KEY_ID=(str, "rzp_test_sample"),
    RAZORPAY_KEY_SECRET=(str, "sample_secret_key"),
    RAZORPAY_WEBHOOK_SECRET=(str, "sample_webhook_secret"),
    STRIPE_PUBLISHABLE_KEY=(str, "pk_test_sample"),
    STRIPE_SECRET_KEY=(str, "sk_test_sample"),
    STRIPE_WEBHOOK_SECRET=(str, "whsec_sample"),
)

# Read .env if present
env_file = BASE_DIR.parent / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

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
    "apps.sharing",
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
    "apps.audit.middleware.AuditLogMiddleware",
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
ASGI_APPLICATION = "config.asgi.application"

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

STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"
WHITENOISE_INDEX_FILE = True
WHITENOISE_ROOT = dist_path if dist_path.exists() else None

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.accounts.authentication.CookieJWTAuthentication",
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
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",
        "user": "1000/day",
        "auth": "10/minute",
        "uploads": "100/minute",
        "share_auth": "10/hour",
    },
    "EXCEPTION_HANDLER": "apps.common.exceptions.custom_exception_handler",
}

# SimpleJWT Settings
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
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

# Celery Configuration
CELERY_BROKER_URL = env("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

# Object Storage (R2 / MinIO)
S3_ENDPOINT_URL = env("S3_ENDPOINT_URL")
S3_ACCESS_KEY_ID = env("S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = env("S3_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = env("S3_BUCKET_NAME")
S3_REGION_NAME = env("S3_REGION_NAME")
PRESIGNED_URL_TTL = env("PRESIGNED_URL_TTL")

# Payments (Razorpay)
PAYMENT_PROVIDER = env("PAYMENT_PROVIDER")
DEFAULT_CURRENCY = env("DEFAULT_CURRENCY")
RAZORPAY_KEY_ID = env("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = env("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = env("RAZORPAY_WEBHOOK_SECRET")
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET")
 
# SpaceByte Cloud Storage Upstream Integration
SPACEBYTE_BASE_URL = env("SPACEBYTE_BASE_URL")
SPACEBYTE_ACCESS_TOKEN = env("SPACEBYTE_ACCESS_TOKEN")
SPACEBYTE_STORAGE_POOL_LIMIT_BYTES = env("SPACEBYTE_STORAGE_POOL_LIMIT_BYTES")
SPACEBYTE_PARENT_FOLDER_ID = env("SPACEBYTE_PARENT_FOLDER_ID")
