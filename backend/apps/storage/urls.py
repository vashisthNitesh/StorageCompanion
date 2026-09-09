from django.urls import path
from apps.storage.views import (
    NodeListView,
    NodeDetailView,
    NodeRestoreView,
    NodeVersionsView,
    NodeDownloadView,
    UploadInitView,
    UploadCompleteView,
    UploadAbortView,
    QuotaView,
    StoragePoolStatusView,
)

urlpatterns = [
    # Nodes (folders & files)
    path("nodes", NodeListView.as_view(), name="node-list"),
    path("nodes/<uuid:pk>", NodeDetailView.as_view(), name="node-detail"),
    path("nodes/<uuid:pk>/restore", NodeRestoreView.as_view(), name="node-restore"),
    path("nodes/<uuid:pk>/versions", NodeVersionsView.as_view(), name="node-versions"),
    path("nodes/<uuid:pk>/download", NodeDownloadView.as_view(), name="node-download"),
    
    # Upload Pipeline (Direct to SpaceByte S3 upstream)
    path("uploads", UploadInitView.as_view(), name="upload-init"),
    path("uploads/<uuid:upload_id>/complete", UploadCompleteView.as_view(), name="upload-complete"),
    path("uploads/<uuid:upload_id>", UploadAbortView.as_view(), name="upload-abort"),
    
    # Quota & SpaceByte Pool
    path("quota", QuotaView.as_view(), name="storage-quota"),
    path("pool-status", StoragePoolStatusView.as_view(), name="storage-pool-status"),
    path("storage/pool-status", StoragePoolStatusView.as_view(), name="storage-pool-status-alias"),
]
