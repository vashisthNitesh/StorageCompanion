from django.urls import path

from apps.links.views import NodeShareListView, PublicShareContentView, PublicShareOpenView, PublicShareView, ShareRevokeView

urlpatterns = [
    path("nodes/<uuid:pk>/shares", NodeShareListView.as_view(), name="node-shares"),
    path("shares/<uuid:link_id>", ShareRevokeView.as_view(), name="share-revoke"),
    path("s/<str:token>", PublicShareView.as_view(), name="share-public"),
    path("s/<str:token>/open", PublicShareOpenView.as_view(), name="share-open"),
    path("s/<str:token>/content", PublicShareContentView.as_view(), name="share-content"),
]
