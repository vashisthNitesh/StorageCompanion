from rest_framework import permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.throttles import ScopedIPThrottle
from apps.links import services
from apps.links.models import ShareLink
from apps.links.serializers import ShareCreateSerializer, ShareLinkSerializer
from apps.storage.models import Node
from apps.storage.views import stream_node_content


class NodeShareListView(APIView):
    """The owner's links for one file (GET) and creating a new one (POST)."""
    permission_classes = [permissions.IsAuthenticated]

    def _node(self, request, pk) -> Node:
        node = Node.objects.filter(id=pk, owner=request.user, deleted_at__isnull=True).first()
        if node is None:
            raise NotFound("File not found.")
        return node

    def get(self, request, pk):
        node = self._node(request, pk)
        links = ShareLink.objects.filter(file=node, created_by=request.user, revoked_at__isnull=True).select_related("file", "file__owner")
        return Response(ShareLinkSerializer(links, many=True).data)

    def post(self, request, pk):
        node = self._node(request, pk)
        serializer = ShareCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        link = services.create_share(request.user, node, serializer.validated_data)
        return Response(ShareLinkSerializer(link).data, status=status.HTTP_201_CREATED)


class ShareRevokeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, link_id):
        services.revoke_share(request.user, link_id)
        return Response({"success": True})


class PublicShareMixin:
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedIPThrottle]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        response["Referrer-Policy"] = "no-referrer"
        return response


class PublicShareView(PublicShareMixin, APIView):
    throttle_scope = "share_public"

    def get(self, request, token):
        return Response(services.public_info(token))


class PublicShareOpenView(PublicShareMixin, APIView):
    throttle_scope = "share_public"

    def post(self, request, token):
        return Response(services.open_share(token, str(request.data.get("password_proof") or "")))


class PublicShareContentView(PublicShareMixin, APIView):
    """Encrypted bytes for a link that was opened. The grant travels in a header, not the URL."""
    throttle_scope = "share_content"

    def get(self, request, token):
        link = services.link_for_grant(token, request.headers.get("X-Share-Grant", ""))
        return stream_node_content(link.file, request.META.get("HTTP_RANGE"))
