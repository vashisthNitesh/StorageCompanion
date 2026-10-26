import logging
from django.http import StreamingHttpResponse
from django.utils import timezone
from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound, ValidationError

from apps.accounts.serializers import UserSerializer
from apps.storage import transfers
from apps.storage.models import Node, FileVersion, StorageQuota, Upload
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
    move_node,
    init_multipart_upload,
    complete_multipart_upload,
    abort_multipart_upload,
    relay_upload_part,
    get_download_info,
    delete_spacebyte_entries_for_nodes,
    restore_spacebyte_entries_for_nodes,
    recalculate_user_quota,
    get_node_descendants,
)
from apps.storage.spacebyte import get_spacebyte_client
from apps.audit.models import AuditLog


logger = logging.getLogger(__name__)


class NodeListView(generics.ListCreateAPIView):
    """
    Lists the user's folders and files. Names are encrypted, so the browser needs every
    item to sort, filter and search; results are therefore not paginated.
    """
    serializer_class = NodeSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        queryset = Node.objects.filter(owner=user, deleted_at__isnull=True)

        if self.request.query_params.get("trashed") == "true":
            # Only top-level trashed items: children of a trashed folder are restored with it.
            return queryset.filter(trashed_at__isnull=False).exclude(parent__trashed_at__isnull=False)

        queryset = queryset.filter(trashed_at__isnull=True)
        parent_param = self.request.query_params.get("parent")
        if parent_param:
            return queryset.filter(parent_id=parent_param)
        if self.request.query_params.get("all") == "true":
            return queryset
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
            move_node(node, request.user, data["parent"])

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
        is_permanent = request.query_params.get("permanent") == "true" or node.trashed_at is not None

        affected_nodes = [node]
        if node.type == Node.TYPE_FOLDER:
            affected_nodes.extend(get_node_descendants(node))

        if is_permanent:
            delete_spacebyte_entries_for_nodes(affected_nodes, delete_forever=True)

            node_id_str = str(node.id)
            node.delete()
            recalculate_user_quota(request.user)

            AuditLog.objects.create(
                user=request.user,
                action="node.deleted_permanently",
                target_type="node",
                target_id=node_id_str,
            )
            return Response({
                "success": True,
                "message": "Permanently deleted.",
                "quota": UserSerializer(request.user).get_quota(request.user),
            })

        # Soft delete: move to trash in-app and on SpaceByte
        now = timezone.now()
        Node.objects.filter(id__in=[n.id for n in affected_nodes]).update(trashed_at=now)
        delete_spacebyte_entries_for_nodes(affected_nodes, delete_forever=False)
        recalculate_user_quota(request.user)

        AuditLog.objects.create(
            user=request.user,
            action="node.trashed",
            target_type="node",
            target_id=str(node.id),
        )
        return Response({
            "success": True,
            "message": "Moved to trash.",
            "quota": UserSerializer(request.user).get_quota(request.user),
        })


class NodeRestoreView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        node = Node.objects.filter(id=pk, owner=request.user, deleted_at__isnull=True).first()
        if not node:
            raise NotFound("Node not found.")

        affected_nodes = [node]
        if node.type == Node.TYPE_FOLDER:
            affected_nodes.extend(get_node_descendants(node))

        Node.objects.filter(id__in=[n.id for n in affected_nodes]).update(trashed_at=None)
        # If the original folder is still in the trash, restore the item to the top level.
        if node.parent_id and Node.objects.filter(id=node.parent_id, trashed_at__isnull=False).exists():
            Node.objects.filter(id=node.id).update(parent=None)

        restore_spacebyte_entries_for_nodes(affected_nodes)
        recalculate_user_quota(request.user)

        AuditLog.objects.create(
            user=request.user,
            action="node.restored",
            target_type="node",
            target_id=str(node.id),
        )
        return Response({
            "success": True,
            "message": "Restored from trash.",
            "quota": UserSerializer(request.user).get_quota(request.user),
        })


class NodeVersionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        node = Node.objects.filter(id=pk, owner=request.user, deleted_at__isnull=True).first()
        if not node:
            raise NotFound("Node not found.")
        versions = FileVersion.objects.filter(node=node)
        return Response(FileVersionSerializer(versions, many=True).data)


def parse_version(request) -> int | None:
    raw = request.query_params.get("v")
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        raise ValidationError("Invalid version number.")


class NodeDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        node = Node.objects.filter(id=pk, owner=request.user, deleted_at__isnull=True).first()
        if not node:
            raise NotFound("Node not found.")

        download_info = get_download_info(node=node, user=request.user, version_no=parse_version(request))

        # The browser also fetches keys to draw thumbnails, open the in-app viewer and create
        # share links. Thumbnails aren't something the person did, and sharing is logged when
        # the link is created, so neither is logged here.
        purpose = request.query_params.get("purpose", "download")
        if purpose not in ("thumbnail", "share"):
            AuditLog.objects.create(
                user=request.user,
                action="file.previewed" if purpose == "preview" else "file.downloaded",
                target_type="node",
                target_id=str(node.id),
            )
        return Response(download_info)


def stream_node_content(node: Node, range_header: str | None):
    """
    Streams a file's encrypted bytes from SpaceByte (with HTTP range support). Callers check
    access first; the browser decrypts, so the server never sees plaintext.
    """
    if not node.spacebyte_hash:
        return Response({"error": "This file's content is not available."}, status=status.HTTP_404_NOT_FOUND)

    if not transfers.acquire(transfers.DOWNLOAD):
        return transfers.busy_response()
    sb_client = get_spacebyte_client()
    try:
        upstream_resp, resp_status, resp_headers = sb_client.download_stream(
            node.spacebyte_hash,
            range_header=range_header,
            timeout=60,
        )
    except Exception as e:
        transfers.release(transfers.DOWNLOAD)
        logger.warning("SpaceByte download stream failed for node %s: %s", node.id, e)
        if not sb_client.is_configured:
            return Response(
                {"error": "File storage is not configured on the server.", "code": "spacebyte_not_configured"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        upstream_status = getattr(e, "status_code", None)
        if upstream_status == 404:
            return Response({"error": "This file was not found in storage."}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {"error": "Could not download this file from storage. Please try again."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    # The slot is held while the body streams and freed when the response closes.
    streaming_resp = StreamingHttpResponse(
        transfers.ReleasingStream(upstream_resp),
        status=resp_status,
        content_type="application/octet-stream",
    )
    if resp_headers.get("Content-Length"):
        streaming_resp["Content-Length"] = resp_headers["Content-Length"]
    if resp_headers.get("Content-Range"):
        streaming_resp["Content-Range"] = resp_headers["Content-Range"]
    streaming_resp["Accept-Ranges"] = resp_headers.get("Accept-Ranges", "bytes")
    streaming_resp["Cache-Control"] = "no-store"
    return streaming_resp


class NodeContentView(APIView):
    """
    Streams encrypted file bytes from SpaceByte to the authenticated owner.
    The browser decrypts them; the server never sees plaintext.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        node = Node.objects.filter(id=pk, owner=request.user, deleted_at__isnull=True).first()
        if not node:
            raise NotFound("File not found.")
        if node.type != Node.TYPE_FILE:
            return Response({"error": "Folders cannot be downloaded directly."}, status=status.HTTP_400_BAD_REQUEST)

        versions = FileVersion.objects.filter(node=node)
        version_no = parse_version(request)
        version = versions.filter(version_no=version_no).first() if version_no else versions.order_by("-version_no").first()
        if not version:
            raise NotFound("File version not found.")
        return stream_node_content(node, request.META.get("HTTP_RANGE"))


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
            wrapped_file_key=data["wrapped_file_key"],
            content_nonce=data["content_nonce"],
            checksum=data.get("checksum", ""),
        )
        resp_data = NodeSerializer(node).data
        resp_data["quota"] = UserSerializer(request.user).get_quota(request.user)
        return Response(resp_data, status=status.HTTP_200_OK)


class UploadAbortView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, upload_id):
        abort_multipart_upload(upload_id=upload_id, user=request.user)
        return Response({"success": True, "message": "Upload session aborted."})


class UploadPartRelayView(APIView):
    """
    Receives one encrypted part and streams it to storage while it arrives. The body is
    read straight from the request stream (never parsed into memory), so large parts
    don't use server memory and the upload to storage overlaps the browser's upload.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, upload_id, part_number):
        upload = Upload.objects.filter(id=upload_id, user=request.user).first()
        if not upload:
            raise NotFound("Upload session not found.")
        if upload.status != Upload.STATUS_UPLOADING:
            return Response({"error": "Upload session is not active.", "code": "upload_inactive"}, status=status.HTTP_409_CONFLICT)

        try:
            length = int(request.META.get("CONTENT_LENGTH") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return Response({"error": "No chunk data received."}, status=status.HTTP_411_LENGTH_REQUIRED)

        if not transfers.acquire(transfers.UPLOAD):
            return transfers.busy_response()
        try:
            etag = relay_upload_part(upload, int(part_number), request._request, length)
        finally:
            transfers.release(transfers.UPLOAD)
        return Response({
            "status": "success",
            "part_number": int(part_number),
            "etag": etag,
        })


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
    Returns system-wide SpaceByte storage pool metrics. Restricted to admins.
    """
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]

    def get(self, request):
        stats = StorageQuota.get_global_pool_stats()
        stats["is_connected"] = get_spacebyte_client().is_configured
        stats["billing_intervals_supported"] = ["monthly", "yearly"]
        stats["user_quota"] = StorageQuotaSerializer(
            StorageQuota.objects.get_or_create(user=request.user)[0]
        ).data
        return Response(stats)
