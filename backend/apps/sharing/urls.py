from django.urls import path
from apps.sharing.views import (
    ShareListCreateView,
    ShareDetailView,
    PublicShareInfoView,
    PublicShareAuthView,
    PublicShareDownloadView,
)

urlpatterns = [
    path("shares", ShareListCreateView.as_view(), name="share-list-create"),
    path("shares/<uuid:pk>", ShareDetailView.as_view(), name="share-detail"),
    
    # Public link endpoints (unauthenticated)
    path("public/shares/<str:token>", PublicShareInfoView.as_view(), name="public-share-info"),
    path("public/shares/<str:token>/auth", PublicShareAuthView.as_view(), name="public-share-auth"),
    path("public/shares/<str:token>/download", PublicShareDownloadView.as_view(), name="public-share-download"),
]
