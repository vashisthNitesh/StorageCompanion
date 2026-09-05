from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView

urlpatterns = [
    # Non-default admin path as specified in single-server architecture
    path("django-admin/", admin.site.urls),
    
    # API v1 routes
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.storage.urls")),
    path("api/v1/", include("apps.sharing.urls")),
    path("api/v1/", include("apps.billing.urls")),
    path("api/v1/audit-logs/", include("apps.audit.urls")),

    # SPA catch-all fallback for Vue Router (when served directly through Django / WhiteNoise)
    re_path(r"^(?!api/|django-admin/|static/|assets/).*$", TemplateView.as_view(template_name="index.html"), name="spa-fallback"),
]
