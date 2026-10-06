import logging
import math
import uuid
from datetime import timedelta

import boto3
import urllib3
from botocore.config import Config
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.audit.models import AuditLog
from apps.common.exceptions import (
    QuotaExceededException,
    SubscriptionRequiredException,
    UpstreamStorageError,
)
from apps.storage.models import FileVersion, Node, StorageQuota, Upload
from apps.storage.spacebyte import get_spacebyte_client

logger = logging.getLogger(__name__)


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        region_name=settings.S3_REGION_NAME,
        # Bounded timeouts/retries: the boto defaults (60s connect x several retries) made previews
        # and uploads hang for minutes when the endpoint is unreachable.
        config=Config(
            signature_version="s3v4",
            connect_timeout=5,
            read_timeout=60,
            retries={"max_attempts": 2, "mode": "standard"},
        ),
    )


def check_storage_pool_capacity(needed_bytes: int):
    """
    Checks aggregate usage against the 1 TB SpaceByte testing pool.
    Raises QuotaExceededException if the system storage pool is exhausted.
    """
    stats = StorageQuota.get_global_pool_stats()
    if stats["used_bytes"] + needed_bytes > stats["total_pool_bytes"]:
        raise QuotaExceededException(
            bytes_needed=needed_bytes,
            bytes_remaining=stats["remaining_bytes"],
            detail={
                "error": "spacebyte_pool_limit_exceeded",
                "message": (
                    f"System 1 TB testing storage pool capacity reached. "
                    f"Pool capacity: {stats['total_pool_gb']} GB, Available: {stats['remaining_gb']} GB. "
                    f"Cannot allocate additional storage on SpaceByte upstream."
                ),
                "code": "STORAGE_POOL_LIMIT_EXCEEDED",
            },
        )


def check_quota_available(user, needed_bytes: int):
    """
    Checks that the user has an active subscription, sufficient storage quota,
    and that the global 1 TB SpaceByte testing pool capacity is not exceeded.
    """
    # 1. Check system-wide 1 TB SpaceByte pool capacity
    check_storage_pool_capacity(needed_bytes)

    # 2. Check user subscription status
    subscription = getattr(user, "subscription", None)
    if not subscription or not subscription.is_valid:
        raise SubscriptionRequiredException(
            detail={
                "error": "subscription_required",
                "message": "An active subscription is required to upload files. Please choose a plan.",
                "code": "SUBSCRIPTION_REQUIRED",
            }
        )

    if not subscription.can_upload:
        raise SubscriptionRequiredException(
            detail={
                "error": "account_in_grace_period",
                "message": "Your account is in a grace period. Uploads are disabled until your subscription is renewed.",
                "code": "ACCOUNT_IN_GRACE_PERIOD",
            }
        )

    quota, _ = StorageQuota.objects.get_or_create(
        user=user,
        defaults={"bytes_limit": subscription.plan.storage_bytes},
    )

    # Sync limit with current subscription plan if needed
    if quota.bytes_limit != subscription.plan.storage_bytes:
        quota.bytes_limit = subscription.plan.storage_bytes
        quota.save(update_fields=["bytes_limit"])

    if quota.bytes_used + needed_bytes > quota.bytes_limit:
        raise QuotaExceededException(
            bytes_needed=needed_bytes,
            bytes_remaining=quota.bytes_remaining,
        )

    return quota


def check_max_file_size(user, size_bytes: int):
    """Enforces the subscription plan's max single-file size (Plan.max_file_size)."""
    subscription = getattr(user, "subscription", None)
    plan = getattr(subscription, "plan", None) if subscription else None
    max_size = getattr(plan, "max_file_size", 0) or 0
    if max_size and size_bytes > max_size:
        raise QuotaExceededException(
            detail={
                "error": "file_too_large",
                "message": f"This file exceeds your plan's maximum file size of {round(max_size / (1024 ** 3), 2)} GB.",
                "code": "FILE_TOO_LARGE",
                "max_file_size": max_size,
            }
        )


def is_descendant_or_self(candidate_parent: Node | None, node: Node) -> bool:
    """True when candidate_parent is `node` itself or lies anywhere beneath it (would create a cycle)."""
    seen = set()
    current = candidate_parent
    while current is not None and current.id not in seen:
        if current.id == node.id:
            return True
        seen.add(current.id)
        current = current.parent
    return False


def create_folder(user, encrypted_name: str, name_nonce: str, parent_id: str | None = None) -> Node:
    parent = None
    if parent_id:
        parent = Node.objects.filter(id=parent_id, owner=user, type=Node.TYPE_FOLDER, deleted_at__isnull=True).first()
        if not parent:
            raise NotFound("Parent folder not found.")

    node = Node.objects.create(
        owner=user,
        parent=parent,
        type=Node.TYPE_FOLDER,
        encrypted_name=encrypted_name,
        name_nonce=name_nonce,
        size_bytes=0,
    )

    AuditLog.objects.create(
        user=user,
        action="folder.created",
        target_type="node",
        target_id=str(node.id),
        metadata={"parent_id": str(parent_id) if parent_id else None},
    )
    return node


def init_multipart_upload(
    user,
    encrypted_name: str,
    name_nonce: str,
    size_bytes: int,
    parent_id: str | None = None,
    node_id: str | None = None,
) -> dict:
    """
    Initializes a direct-to-R2 multipart upload.
    Checks quota first and returns presigned PUT URLs for all parts.
    """
    check_quota_available(user, size_bytes)
    check_max_file_size(user, size_bytes)

    parent = None
    if parent_id:
        parent = Node.objects.filter(id=parent_id, owner=user, type=Node.TYPE_FOLDER, deleted_at__isnull=True).first()
        if not parent:
            raise NotFound("Parent folder not found.")

    # New version of an existing file: the target node must belong to the caller (prevents
    # overwriting another user's file by passing their node id).
    if node_id:
        if not Node.objects.filter(id=node_id, owner=user, type=Node.TYPE_FILE, deleted_at__isnull=True).exists():
            raise NotFound("File not found.")

    # Determine chunk size: 8 MB default, 16 MB for files > 5 GB
    part_size = 16 * 1024 * 1024 if size_bytes > 5 * 1024 * 1024 * 1024 else 8 * 1024 * 1024
    num_parts = max(1, math.ceil(size_bytes / part_size))

    sb_client = get_spacebyte_client()
    spacebyte_upload_id = ""
    spacebyte_key = ""
    presigned_urls = []
    expires_at = timezone.now() + timedelta(hours=24)

    if sb_client.is_configured:
        try:
            sb_init = sb_client.init_multipart_upload(
                filename=f"vault_{user.id}_{uuid.uuid4().hex[:8]}.bin",
                mime="application/octet-stream",
                part_count=num_parts,
            )
            s3_upload_id = sb_init["upload_id"]
            object_key = sb_init["key"]
            spacebyte_upload_id = s3_upload_id
            spacebyte_key = object_key
            presigned_urls = [
                {"part_number": p.get("partNumber", p.get("part_number", 1)), "url": p["url"]}
                for p in sb_init.get("presigned_urls", [])
            ]
        except Exception as e:
            logger.warning("SpaceByte init multipart warning: %s; falling back to local S3 engine.", e)
            sb_init = None
    else:
        sb_init = None

    if not sb_init:
        object_key = f"vault/{user.id}/{uuid.uuid4()}"
        bucket = settings.S3_BUCKET_NAME

        s3 = get_s3_client()
        try:
            response = s3.create_multipart_upload(
                Bucket=bucket,
                Key=object_key,
                ContentType="application/octet-stream",
            )
            s3_upload_id = response["UploadId"]
        except Exception as e:
            if not settings.DEBUG:
                logger.error("S3 create_multipart_upload failed: %s", e)
                raise UpstreamStorageError("Storage provider is unavailable. Please try again later.") from e
            # Local development without object storage: simulate the upload
            s3_upload_id = f"mock-upload-{uuid.uuid4()}"

        presigned_urls = []
        for part_num in range(1, num_parts + 1):
            try:
                url = s3.generate_presigned_url(
                    ClientMethod="upload_part",
                    Params={
                        "Bucket": bucket,
                        "Key": object_key,
                        "UploadId": s3_upload_id,
                        "PartNumber": part_num,
                    },
                    ExpiresIn=settings.PRESIGNED_URL_TTL,
                )
            except Exception:
                url = f"{settings.S3_ENDPOINT_URL}/{bucket}/{object_key}?uploadId={s3_upload_id}&partNumber={part_num}"

            presigned_urls.append({
                "part_number": part_num,
                "url": url,
            })

    upload = Upload.objects.create(
        user=user,
        parent_id=parent.id if parent else None,
        node_id=node_id,
        upload_id=s3_upload_id,
        object_key=object_key,
        spacebyte_upload_id=spacebyte_upload_id,
        spacebyte_key=spacebyte_key,
        encrypted_name=encrypted_name,
        name_nonce=name_nonce,
        expected_size_bytes=size_bytes,
        part_size=part_size,
        parts=presigned_urls,
        status=Upload.STATUS_UPLOADING,
        expires_at=expires_at,
    )

    return {
        "upload_session_id": str(upload.id),
        "s3_upload_id": s3_upload_id,
        "object_key": object_key,
        "part_size": part_size,
        "total_parts": num_parts,
        "presigned_urls": presigned_urls,
        "expires_at": expires_at.isoformat(),
        "provider": "spacebyte" if spacebyte_upload_id else "s3",
    }


@transaction.atomic
def complete_multipart_upload(
    upload_id: str,
    user,
    parts: list[dict],
    wrapped_file_key: str,
    content_nonce: str,
    checksum: str = "",
    thumbnail_object_key: str = "",
    thumbnail_nonce: str = "",
) -> Node:
    """
    Commits multipart upload, creates/updates Node, creates FileVersion, and increments quota atomically.
    """
    upload = Upload.objects.select_for_update().filter(id=upload_id, user=user).first()
    if not upload:
        raise NotFound("Upload session not found.")
    if upload.status == Upload.STATUS_COMPLETED:
        return upload.node

    # Quota check again on completion
    check_quota_available(user, upload.expected_size_bytes)

    # Complete multipart upload in SpaceByte / S3
    sb_client = get_spacebyte_client()
    spacebyte_entry = None
    if upload.spacebyte_upload_id:
        try:
            sb_parts = [{"PartNumber": p["part_number"], "ETag": (p.get("etag") or f'"{p["part_number"]}"')} for p in sorted(parts, key=lambda x: x["part_number"])]
            sb_client.complete_multipart_upload(upload.spacebyte_upload_id, upload.spacebyte_key, sb_parts)
            # Create/Register file entry in SpaceByte
            entry_res = sb_client.create_file_entry(
                filename=upload.spacebyte_key,
                client_name=f"vault_{upload.id}.bin",
                size=upload.expected_size_bytes,
                client_mime="application/octet-stream",
                client_extension="bin",
            )
            spacebyte_entry = entry_res.get("fileEntry", {})
        except Exception as e:
            # Do NOT create a file record pointing at data that was never assembled upstream:
            # that produced files which could never be previewed or downloaded.
            logger.error("SpaceByte complete multipart/entry failed for upload %s: %s", upload.id, e)
            raise UpstreamStorageError("Storage provider could not finalize the upload. Please retry.") from e
        if not spacebyte_entry or not spacebyte_entry.get("hash"):
            raise UpstreamStorageError("Storage provider did not register the uploaded file. Please retry.")
    else:
        s3 = get_s3_client()
        is_mock_upload = str(upload.upload_id).startswith("mock-upload-")
        s3_parts = [{"PartNumber": p["part_number"], "ETag": (p.get("etag") or f'"{p["part_number"]}"')} for p in sorted(parts, key=lambda x: x["part_number"])]
        if not is_mock_upload:
            # Browsers often cannot read the ETag of a cross-origin PUT (CORS doesn't expose it), so the
            # client-sent ETags may be placeholders. Ask S3 for the authoritative part list instead.
            try:
                listed = s3.list_parts(Bucket=settings.S3_BUCKET_NAME, Key=upload.object_key, UploadId=upload.upload_id)
                server_parts = [{"PartNumber": p["PartNumber"], "ETag": p["ETag"]} for p in listed.get("Parts", [])]
                if server_parts:
                    s3_parts = server_parts
            except Exception as e:
                logger.warning("list_parts failed for upload %s, using client ETags: %s", upload.id, e)
        try:
            s3.complete_multipart_upload(
                Bucket=settings.S3_BUCKET_NAME,
                Key=upload.object_key,
                UploadId=upload.upload_id,
                MultipartUpload={"Parts": s3_parts},
            )
        except Exception as e:
            if not (settings.DEBUG and is_mock_upload):
                logger.error("S3 complete_multipart_upload failed for upload %s: %s", upload.id, e)
                raise UpstreamStorageError("Storage provider could not finalize the upload. Please retry.") from e

    parent = None
    if upload.parent_id:
        parent = Node.objects.filter(id=upload.parent_id, owner=user, deleted_at__isnull=True).first()

    if upload.node and upload.node.owner_id != user.id:
        raise NotFound("File not found.")

    # Create or update Node
    if upload.node:
        node = upload.node
        node.size_bytes = upload.expected_size_bytes
        node.encrypted_name = upload.encrypted_name
        node.name_nonce = upload.name_nonce
        if spacebyte_entry:
            node.spacebyte_entry_id = spacebyte_entry.get("id")
            node.spacebyte_hash = spacebyte_entry.get("hash", "")
        if thumbnail_object_key:
            node.thumbnail_object_key = thumbnail_object_key
            node.thumbnail_nonce = thumbnail_nonce
        node.save()
    else:
        node = Node.objects.create(
            owner=user,
            parent=parent,
            type=Node.TYPE_FILE,
            encrypted_name=upload.encrypted_name,
            name_nonce=upload.name_nonce,
            size_bytes=upload.expected_size_bytes,
            spacebyte_entry_id=spacebyte_entry.get("id") if spacebyte_entry else None,
            spacebyte_hash=spacebyte_entry.get("hash", "") if spacebyte_entry else "",
            thumbnail_object_key=thumbnail_object_key,
            thumbnail_nonce=thumbnail_nonce,
        )

    # Determine version number
    last_version = FileVersion.objects.filter(node=node).order_by("-version_no").first()
    version_no = (last_version.version_no + 1) if last_version else 1

    FileVersion.objects.create(
        node=node,
        version_no=version_no,
        object_key=upload.object_key,
        spacebyte_file_name=upload.spacebyte_key,
        size_bytes=upload.expected_size_bytes,
        wrapped_file_key=wrapped_file_key,
        content_nonce=content_nonce,
        checksum=checksum,
    )

    # Update quota
    quota, _ = StorageQuota.objects.select_for_update().get_or_create(user=user)
    quota.bytes_used += upload.expected_size_bytes
    quota.save(update_fields=["bytes_used"])

    upload.status = Upload.STATUS_COMPLETED
    upload.node = node
    upload.parts = parts
    upload.save(update_fields=["status", "node", "parts"])

    AuditLog.objects.create(
        user=user,
        action="file.uploaded",
        target_type="node",
        target_id=str(node.id),
        metadata={"version": version_no, "size_bytes": upload.expected_size_bytes, "upstream": "spacebyte" if upload.spacebyte_upload_id else "s3"},
    )

    return node


def abort_multipart_upload(upload_id: str, user):
    upload = Upload.objects.filter(id=upload_id, user=user).first()
    if not upload:
        raise NotFound("Upload session not found.")

    if upload.status == Upload.STATUS_UPLOADING:
        if upload.spacebyte_upload_id:
            try:
                sb_client = get_spacebyte_client()
                sb_client.abort_multipart_upload(upload.spacebyte_upload_id, upload.spacebyte_key)
            except Exception:
                pass
        else:
            s3 = get_s3_client()
            try:
                s3.abort_multipart_upload(
                    Bucket=settings.S3_BUCKET_NAME,
                    Key=upload.object_key,
                    UploadId=upload.upload_id,
                )
            except Exception:
                pass
        upload.status = Upload.STATUS_ABORTED
        upload.save(update_fields=["status"])



http_pool = urllib3.PoolManager(
    maxsize=10,
    timeout=urllib3.Timeout(connect=5.0, read=60.0),
    retries=urllib3.Retry(total=2, backoff_factor=0.5),
)


def relay_upload_part(upload: Upload, part_number: int, chunk_bytes: bytes) -> str:
    """
    Relays an encrypted chunk directly to SpaceByte / S3 upstream when client direct-upload
    fails or is blocked by CORS/network policies. Uses connection pooling for high throughput.
    """
    presigned_url = None
    if isinstance(upload.parts, list):
        for p in upload.parts:
            if isinstance(p, dict) and p.get("part_number") == part_number:
                presigned_url = p.get("url")
                break

    if not presigned_url:
        if upload.spacebyte_upload_id:
            try:
                sb_client = get_spacebyte_client()
                sign_res = sb_client._request(
                    "POST",
                    "s3/multipart/batch-sign-part-urls",
                    {
                        "uploadId": upload.spacebyte_upload_id,
                        "key": upload.spacebyte_key,
                        "partNumbers": [part_number],
                    },
                )
                urls = sign_res.get("urls", [])
                if urls and isinstance(urls[0], dict):
                    presigned_url = urls[0].get("url")
            except Exception as e:
                logger.warning("Failed to get SpaceByte presigned part URL: %s", e)
        else:
            s3 = get_s3_client()
            try:
                presigned_url = s3.generate_presigned_url(
                    ClientMethod="upload_part",
                    Params={
                        "Bucket": settings.S3_BUCKET_NAME,
                        "Key": upload.object_key,
                        "UploadId": upload.upload_id,
                        "PartNumber": part_number,
                    },
                    ExpiresIn=settings.PRESIGNED_URL_TTL,
                )
            except Exception:
                presigned_url = f"{settings.S3_ENDPOINT_URL}/{settings.S3_BUCKET_NAME}/{upload.object_key}?uploadId={upload.upload_id}&partNumber={part_number}"

    if not presigned_url:
        raise UpstreamStorageError(f"Could not obtain an upload URL for part {part_number}.")
    # Mock URLs only exist when no real storage is configured (DEBUG-only mock uploads / unconfigured SpaceByte client)
    if (
        presigned_url.startswith("https://mock-s3.local")
        or "mock-upload-" in presigned_url
        or "mockSign=valid" in presigned_url
    ):
        # Local development without object storage: simulate success
        return f'"{part_number}"'

    try:
        resp = http_pool.request(
            "PUT",
            presigned_url,
            body=chunk_bytes,
            headers={"Content-Type": "application/octet-stream"},
        )
    except Exception as e:
        logger.error("Failed to relay upload part %s to upstream: %s", part_number, e)
        raise UpstreamStorageError(f"Storage provider unreachable while uploading part {part_number}.") from e

    if resp.status in (200, 201, 204):
        etag = resp.headers.get("ETag")
        if not etag:
            raise UpstreamStorageError(f"Storage provider returned no ETag for part {part_number}.")
        return etag.strip()
    logger.error("Upstream returned HTTP %s for part %s", resp.status, part_number)
    # Never report success with a fabricated ETag: that silently produced corrupt/missing files.
    raise UpstreamStorageError(f"Storage provider rejected part {part_number} (HTTP {resp.status}).")


def get_download_info(node: Node, user, version_no: int | None = None) -> dict:
    """
    Generates a download URL from SpaceByte or presigned S3 URL along with the encrypted File Key, nonce, and part_size.
    Always provides the authenticated content stream URL as the primary download_url to prevent 401 and CORS errors.
    """
    if node.owner != user:
        raise PermissionDenied("You do not have permission to access this file.")
    if node.type != Node.TYPE_FILE:
        raise NotFound("Folders cannot be downloaded directly.")

    versions = FileVersion.objects.filter(node=node)
    if version_no:
        version = versions.filter(version_no=version_no).first()
    else:
        version = versions.order_by("-version_no").first()

    if not version:
        raise NotFound("File version not found.")

    part_size = 16 * 1024 * 1024 if version.size_bytes > 5 * 1024 * 1024 * 1024 else 8 * 1024 * 1024

    if node.spacebyte_hash:
        sb_client = get_spacebyte_client()
        resolved_url = sb_client.resolve_direct_download_url(node.spacebyte_hash)
        direct_download_url = resolved_url or sb_client.get_download_url(node.spacebyte_hash)
    else:
        s3 = get_s3_client()
        try:
            direct_download_url = s3.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": settings.S3_BUCKET_NAME, "Key": version.object_key},
                ExpiresIn=settings.PRESIGNED_URL_TTL,
            )
        except Exception:
            # An unsigned URL to a private bucket can never work; let the client use the proxy
            direct_download_url = None

    # Primary download URL routes through authenticated backend streaming proxy
    stream_url = f"/api/v1/nodes/{node.id}/content" + (f"?v={version.version_no}" if version_no else "")

    return {
        "node_id": str(node.id),
        "version_no": version.version_no,
        "size_bytes": version.size_bytes,
        "part_size": part_size,
        "wrapped_file_key": version.wrapped_file_key,
        "content_nonce": version.content_nonce,
        "download_url": stream_url,
        "direct_url": direct_download_url,
        "expires_in": settings.PRESIGNED_URL_TTL,
        "upstream": "spacebyte" if node.spacebyte_hash else "s3",
    }
