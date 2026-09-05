from .base import *

DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "web", ".onrender.com", "*"],
)
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["https://*.onrender.com", "http://localhost:5173"],
)

# Cookie security (secure on HTTPS)
SIMPLE_JWT["AUTH_COOKIE_SECURE"] = env.bool("COOKIE_SECURE", default=True)
SESSION_COOKIE_SECURE = env.bool("COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = env.bool("COOKIE_SECURE", default=True)

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSP headers
CSP_DEFAULT_SRC = ("'self'",)
CSP_STYLE_SRC = ("'self'", "https://fonts.googleapis.com", "'unsafe-inline'")
CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com")
CSP_IMG_SRC = ("'self'", "data:", "blob:", "https://images.unsplash.com")
CSP_CONNECT_SRC = ("'self'", "https://*.r2.cloudflarestorage.com", "https://api.razorpay.com")
CSP_SCRIPT_SRC = ("'self'", "https://checkout.razorpay.com")
