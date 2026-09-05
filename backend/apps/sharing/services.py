import hashlib
import secrets
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.storage.models import Node, FileVersion
from apps.sharing.models import Share
from apps.storage.services import get_s3_client
from apps.audit.models import AuditLog


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_public_link_share(
    user: User,
    node_id: str,
    wrapped_key: str,
    permission: str = Share.PERM_DOWNLOAD,
    password: str | None = None,
    expires_at=None,
    max_downloads: int | None = None,
) -> tuple[Share, str]:
    node = Node.objects.filter(id=node_id, owner=user, deleted_at__isnull=True).first()
    if not node:
        raise NotFound("File or folder not found.")

    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_token(raw_token)

    pw_hash = make_password(password) if password else None

    share = Share.objects.create(
        node=node,
        created_by=user,
        type=Share.TYPE_LINK,
        wrapped_key=wrapped_key,
        link_token_hash=token_hash,
        permission=permission,
        password_hash=pw_hash,
        expires_at=expires_at,
        max_downloads=max_downloads,
    )

    AuditLog.objects.create(
        user=user,
        action="share.link_created",
        target_type="share",
        target_id=str(share.id),
        metadata={"node_id": str(node.id), "permission": permission},
    )

    return share, raw_token


def create_user_share(
    user: User,
    node_id: str,
    recipient_email: str,
    wrapped_key: str,
    permission: str = Share.PERM_DOWNLOAD,
    expires_at=None,
) -> Share:
    node = Node.objects.filter(id=node_id, owner=user, deleted_at__isnull=True).first()
    if not node:
        raise NotFound("File or folder not found.")

    recipient = User.objects.filter(email=recipient_email.lower().strip()).first()
    if not recipient:
        raise NotFound("Recipient user not found.")
    if recipient == user:
        raise ValidationError("Cannot share file with yourself.")

    share = Share.objects.create(
        node=node,
        created_by=user,
        type=Share.TYPE_USER,
        recipient=recipient,
        wrapped_key=wrapped_key,
        permission=permission,
        expires_at=expires_at,
    )

    AuditLog.objects.create(
        user=user,
        action="share.user_created",
        target_type="share",
        target_id=str(share.id),
        metadata={"node_id": str(node.id), "recipient": recipient.email},
    )

    return share


def get_public_share_info(token: str, password: str | None = None) -> dict:
    token_hash = hash_token(token)
    share = Share.objects.filter(link_token_hash=token_hash).first()
    if not share or not share.is_active:
        raise NotFound("Share link is invalid, expired, or has reached its download limit.")

    requires_password = share.password_hash is not None
    is_authenticated = False

    if requires_password:
        if password:
            if not check_password(password, share.password_hash):
                raise PermissionDenied("Incorrect password.")
            is_authenticated = True
    else:
        is_authenticated = True

    node = share.node
    version = FileVersion.objects.filter(node=node).order_by("-version_no").first()

    return {
        "share_id": str(share.id),
        "node_id": str(node.id),
        "type": node.type,
        "encrypted_name": node.encrypted_name,
        "name_nonce": node.name_nonce,
        "size_bytes": node.size_bytes,
        "permission": share.permission,
        "requires_password": requires_password,
        "is_authenticated": is_authenticated,
        "wrapped_key": share.wrapped_key if is_authenticated else None,
        "content_nonce": version.content_nonce if (is_authenticated and version) else None,
        "expires_at": share.expires_at.isoformat() if share.expires_at else None,
    }


def get_public_download_url(token: str, password: str | None = None) -> dict:
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

    s3 = get_s3_client()
    try:
        presigned_url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": version.object_key},
            ExpiresIn=settings.PRESIGNED_URL_TTL,
        )
    except Exception:
        presigned_url = f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET_NAME}/{version.object_key}"

    # Increment download count
    share.download_count += 1
    share.save(update_fields=["download_count"])

    return {
        "download_url": presigned_url,
        "wrapped_key": share.wrapped_key,
        "content_nonce": version.content_nonce,
        "size_bytes": version.size_bytes,
        "expires_in": settings.PRESIGNED_URL_TTL,
    }
