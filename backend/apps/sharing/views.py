import urllib.request
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.db.models import Q
from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.sharing.models import Share
from apps.storage.models import FileVersion
from apps.storage.spacebyte import get_spacebyte_client
from apps.storage.services import get_s3_client
from apps.sharing.serializers import (
    ShareSerializer,
    CreateShareSerializer,
    PublicShareAuthSerializer,
)
from apps.sharing.services import (
    create_public_link_share,
    create_user_share,
    get_public_share_info,
    get_public_download_url,
    hash_token,
)
from apps.audit.models import AuditLog


class ShareListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        mode = request.query_params.get("filter", "all")
        user = request.user

        if mode == "created":
            shares = Share.objects.filter(created_by=user, revoked_at__isnull=True)
        elif mode == "received":
            shares = Share.objects.filter(recipient=user, revoked_at__isnull=True)
        else:
            shares = Share.objects.filter(
                Q(created_by=user) | Q(recipient=user),
                revoked_at__isnull=True,
            )

        return Response(ShareSerializer(shares, many=True).data)

    def post(self, request):
        serializer = CreateShareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data["type"] == Share.TYPE_LINK:
            share, raw_token = create_public_link_share(
                user=request.user,
                node_id=data["node_id"],
                wrapped_key=data["wrapped_key"],
                permission=data.get("permission", Share.PERM_DOWNLOAD),
                password=data.get("password"),
                expires_at=data.get("expires_at"),
                max_downloads=data.get("max_downloads"),
            )
            resp_data = ShareSerializer(share).data
            resp_data["raw_token"] = raw_token
            return Response(resp_data, status=status.HTTP_201_CREATED)
        else:
            share = create_user_share(
                user=request.user,
                node_id=data["node_id"],
                recipient_email=data.get("recipient_email", ""),
                wrapped_key=data["wrapped_key"],
                permission=data.get("permission", Share.PERM_DOWNLOAD),
                expires_at=data.get("expires_at"),
            )
            return Response(ShareSerializer(share).data, status=status.HTTP_201_CREATED)


class ShareDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_share(self, pk, user):
        share = Share.objects.filter(
            Q(id=pk) & (Q(created_by=user) | Q(recipient=user))
        ).first()
        if not share:
            raise NotFound("Share not found.")
        return share

    def get(self, request, pk):
        share = self.get_share(pk, request.user)
        return Response(ShareSerializer(share).data)

    def delete(self, request, pk):
        share = Share.objects.filter(id=pk, created_by=request.user).first()
        if not share:
            raise NotFound("Share not found.")

        share.revoked_at = timezone.now()
        share.save(update_fields=["revoked_at"])

        AuditLog.objects.create(
            user=request.user,
            action="share.revoked",
            target_type="share",
            target_id=str(share.id),
        )
        return Response({"success": True, "message": "Share revoked."})


class PublicShareInfoView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        password = request.query_params.get("password")
        info = get_public_share_info(token=token, password=password)
        return Response(info)


class PublicShareAuthView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, token):
        serializer = PublicShareAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data["password"]

        info = get_public_share_info(token=token, password=password)
        return Response(info)


class PublicShareDownloadView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        password = request.query_params.get("password")
        download_data = get_public_download_url(token=token, password=password)
        return Response(download_data)


class PublicShareContentView(APIView):
    """
    Streams encrypted file bytes for public shares directly to the browser.
    Validates token & optional password, then proxies from SpaceByte / S3 upstream.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, token):
        password = request.query_params.get("password")
        token_hash = hash_token(token)
        share = Share.objects.filter(link_token_hash=token_hash).first()
        if not share or not share.is_active:
            raise NotFound("Share link is invalid or expired.")

        if share.password_hash:
            if not password or not check_password(password, share.password_hash):
                raise PermissionDenied("Password required or incorrect.")

        node = share.node
        version = FileVersion.objects.filter(node=node).order_by("-version_no").first()
        if not version:
            raise NotFound("File content not found.")

        def _stream_s3():
            s3 = get_s3_client()
            params = {"Bucket": settings.S3_BUCKET_NAME, "Key": version.object_key}
            if "HTTP_RANGE" in request.META:
                params["Range"] = request.META["HTTP_RANGE"]
            s3_obj = s3.get_object(**params)
            status_code = 206 if "Range" in params else 200
            streaming_resp = StreamingHttpResponse(
                s3_obj["Body"].iter_chunks(chunk_size=128 * 1024),
                status=status_code,
                content_type="application/octet-stream",
            )
            if "ContentLength" in s3_obj:
                streaming_resp["Content-Length"] = str(s3_obj["ContentLength"])
            if "ContentRange" in s3_obj:
                streaming_resp["Content-Range"] = str(s3_obj["ContentRange"])
            streaming_resp["Accept-Ranges"] = "bytes"
            streaming_resp["Access-Control-Allow-Origin"] = "*"
            return streaming_resp

        # Stream from SpaceByte upstream if hash is registered
        if node.spacebyte_hash:
            sb_client = get_spacebyte_client()
            upstream_url = sb_client.get_download_url(node.spacebyte_hash)
            headers = sb_client._headers(content_type="")
            if "HTTP_RANGE" in request.META:
                headers["Range"] = request.META["HTTP_RANGE"]

            req = urllib.request.Request(upstream_url, headers=headers)
            try:
                upstream_resp = urllib.request.urlopen(req, timeout=60)
                streaming_resp = StreamingHttpResponse(
                    iter(lambda: upstream_resp.read(128 * 1024), b""),
                    status=upstream_resp.status,
                    content_type="application/octet-stream",
                )
                if upstream_resp.headers.get("Content-Length"):
                    streaming_resp["Content-Length"] = upstream_resp.headers.get("Content-Length")
                if upstream_resp.headers.get("Content-Range"):
                    streaming_resp["Content-Range"] = upstream_resp.headers.get("Content-Range")
                streaming_resp["Accept-Ranges"] = "bytes"
                streaming_resp["Access-Control-Allow-Origin"] = "*"
                return streaming_resp
            except Exception as e:
                logger.warning("SpaceByte public share stream failed (%s), attempting S3 fallback: %s", type(e).__name__, e)
                if version and version.object_key:
                    try:
                        return _stream_s3()
                    except Exception as s3_err:
                        logger.error("S3 fallback share stream failed: %s", s3_err)
                return Response({"error": "Failed to stream file from storage."}, status=status.HTTP_502_BAD_GATEWAY)
        else:
            try:
                return _stream_s3()
            except Exception as e:
                logger.error("Failed to retrieve file from S3: %s", e)
                return Response({"error": "Failed to retrieve file from storage."}, status=status.HTTP_502_BAD_GATEWAY)
