from django.utils import timezone
from django.db.models import Q
from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.sharing.models import Share
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
