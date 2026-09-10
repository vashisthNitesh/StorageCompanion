from django.utils import timezone
from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.storage.models import Node, FileVersion, StorageQuota
from apps.storage.serializers import (
    NodeSerializer,
    FileVersionSerializer,
    CreateFolderSerializer,
    UpdateNodeSerializer,
    InitUploadSerializer,
    CompleteUploadSerializer,
    StorageQuotaSerializer,
)
from apps.storage.services import (
    create_folder,
    init_multipart_upload,
    complete_multipart_upload,
    abort_multipart_upload,
    get_download_info,
)
from apps.audit.models import AuditLog


class NodeListView(generics.ListCreateAPIView):
    serializer_class = NodeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Node.objects.filter(owner=user, deleted_at__isnull=True)

        is_trashed = self.request.query_params.get("trashed") == "true"
        if is_trashed:
            return queryset.filter(trashed_at__isnull=False)
        else:
            queryset = queryset.filter(trashed_at__isnull=True)

        parent_param = self.request.query_params.get("parent")
        if parent_param:
            return queryset.filter(parent_id=parent_param)
        elif self.request.query_params.get("all") == "true":
            return queryset
        else:
            # Root directory by default
            return queryset.filter(parent__isnull=True)

    def create(self, request, *args, **kwargs):
        serializer = CreateFolderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        node = create_folder(
            user=request.user,
            encrypted_name=serializer.validated_data["encrypted_name"],
            name_nonce=serializer.validated_data["name_nonce"],
            parent_id=serializer.validated_data.get("parent"),
        )
        return Response(NodeSerializer(node).data, status=status.HTTP_201_CREATED)


class NodeDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_node(self, pk, user):
        node = Node.objects.filter(id=pk, owner=user, deleted_at__isnull=True).first()
        if not node:
            raise NotFound("File or folder not found.")
        return node

    def get(self, request, pk):
        node = self.get_node(pk, request.user)
        return Response(NodeSerializer(node).data)

    def patch(self, request, pk):
        node = self.get_node(pk, request.user)
        serializer = UpdateNodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if "encrypted_name" in data:
            node.encrypted_name = data["encrypted_name"]
            node.name_nonce = data.get("name_nonce", node.name_nonce)
        if "parent" in data:
            parent_id = data["parent"]
            parent = None
            if parent_id:
                parent = Node.objects.filter(id=parent_id, owner=request.user, type=Node.TYPE_FOLDER).first()
                if not parent:
                    return Response({"error": "Target parent folder not found."}, status=400)
            node.parent = parent

        node.save()
        AuditLog.objects.create(
            user=request.user,
            action="node.updated",
            target_type="node",
            target_id=str(node.id),
        )
        return Response(NodeSerializer(node).data)

    def delete(self, request, pk):
        node = self.get_node(pk, request.user)
        # Soft delete: move to trash
        node.trashed_at = timezone.now()
        node.save(update_fields=["trashed_at"])

        AuditLog.objects.create(
            user=request.user,
            action="node.trashed",
            target_type="node",
            target_id=str(node.id),
        )
        return Response({"success": True, "message": "Moved to trash."})


class NodeRestoreView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        node = Node.objects.filter(id=pk, owner=request.user, deleted_at__isnull=True).first()
        if not node:
            raise NotFound("Node not found.")

        node.trashed_at = None
        node.save(update_fields=["trashed_at"])

        AuditLog.objects.create(
            user=request.user,
            action="node.restored",
            target_type="node",
            target_id=str(node.id),
        )
        return Response({"success": True, "message": "Restored from trash."})


class NodeVersionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        node = Node.objects.filter(id=pk, owner=request.user, deleted_at__isnull=True).first()
        if not node:
            raise NotFound("Node not found.")
        versions = FileVersion.objects.filter(node=node)
        return Response(FileVersionSerializer(versions, many=True).data)


class NodeDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        node = Node.objects.filter(id=pk, owner=request.user, deleted_at__isnull=True).first()
        if not node:
            raise NotFound("Node not found.")

        version_no = request.query_params.get("v")
        download_info = get_download_info(
            node=node,
            user=request.user,
            version_no=int(version_no) if version_no else None,
        )

        AuditLog.objects.create(
            user=request.user,
            action="file.downloaded",
            target_type="node",
            target_id=str(node.id),
        )
        return Response(download_info)


class UploadInitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = InitUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        upload_data = init_multipart_upload(
            user=request.user,
            encrypted_name=data["encrypted_name"],
            name_nonce=data["name_nonce"],
            size_bytes=data["size_bytes"],
            parent_id=data.get("parent_id"),
            node_id=data.get("node_id"),
        )
        return Response(upload_data, status=status.HTTP_201_CREATED)


class UploadCompleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, upload_id):
        serializer = CompleteUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        node = complete_multipart_upload(
            upload_id=upload_id,
            user=request.user,
            parts=data["parts"],
            wrapped_file_key=data["wrapped_file_key"],
            content_nonce=data["content_nonce"],
            checksum=data.get("checksum", ""),
            thumbnail_object_key=data.get("thumbnail_object_key", ""),
            thumbnail_nonce=data.get("thumbnail_nonce", ""),
        )
        return Response(NodeSerializer(node).data, status=status.HTTP_200_OK)


class UploadAbortView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, upload_id):
        abort_multipart_upload(upload_id=upload_id, user=request.user)
        return Response({"success": True, "message": "Upload session aborted."})


class QuotaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        quota, _ = StorageQuota.objects.get_or_create(user=request.user)
        subscription = getattr(request.user, "subscription", None)

        if subscription and subscription.plan and subscription.is_valid:
            if quota.bytes_limit != subscription.plan.storage_bytes:
                quota.bytes_limit = subscription.plan.storage_bytes
                quota.save(update_fields=["bytes_limit"])
        elif subscription and not subscription.is_valid:
            # When subscription is expired or lapsed, retain existing files without deleting them,
            # but reclaim any unused reservation back into the pool.
            effective_limit = max(0, quota.bytes_used)
            if quota.bytes_limit != effective_limit:
                quota.bytes_limit = effective_limit
                quota.save(update_fields=["bytes_limit"])

        data = StorageQuotaSerializer(quota).data
        if subscription:
            data["subscription_status"] = subscription.status
            data["can_upload"] = subscription.can_upload
            data["is_in_grace_period"] = subscription.is_in_grace_period
            data["grace_period_ends_at"] = subscription.grace_period_ends_at
        else:
            data["subscription_status"] = "none"
            data["can_upload"] = False
            data["is_in_grace_period"] = False
            data["grace_period_ends_at"] = None

        return Response(data)


class StoragePoolStatusView(APIView):
    """
    Returns system-wide 1 TB SpaceByte testing storage pool metrics,
    connection health, user quota summary, and supported billing intervals.
    Restricted exclusively to Master Admins.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request):
        stats = StorageQuota.get_global_pool_stats()
        from apps.storage.spacebyte import get_spacebyte_client
        sb_client = get_spacebyte_client()
        stats["is_connected"] = sb_client.is_configured
        stats["billing_intervals_supported"] = ["monthly", "yearly"]
        stats["user_quota"] = StorageQuotaSerializer(
            getattr(request.user, "storage_quota", None) or StorageQuota.objects.get_or_create(user=request.user)[0]
        ).data
        return Response(stats)
