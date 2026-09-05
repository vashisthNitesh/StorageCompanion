from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Non-default admin path as specified in single-server architecture
    path("django-admin/", admin.site.urls),
    
    # API v1 routes
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.storage.urls")),
    path("api/v1/", include("apps.sharing.urls")),
    path("api/v1/", include("apps.billing.urls")),
    path("api/v1/audit-logs/", include("apps.audit.urls")),
]
