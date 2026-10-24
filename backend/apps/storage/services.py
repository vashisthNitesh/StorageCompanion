import logging
import math
import threading
import time
import uuid
from datetime import timedelta

import urllib3
from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.common.exceptions import IncompletePartError, QuotaExceededException, SubscriptionRequiredException, UpstreamStorageError
from apps.storage.models import Node, FileVersion, Upload, StorageQuota
from apps.storage.spacebyte import SpaceByteError, get_spacebyte_client
from apps.audit.models import AuditLog

logger = logging.getLogger(__name__)

# AES-256-GCM appends a 16-byte authentication tag to every encrypted part.
GCM_TAG_BYTES = 16


def upstream_error(message: str) -> UpstreamStorageError:
    return UpstreamStorageError(
        detail={"error": "upstream_storage_error", "message": message, "code": "UPSTREAM_STORAGE_ERROR"}
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
                "error": "storage_pool_limit_exceeded",
                "message": "The service is temporarily out of storage capacity. Please try again later.",
                "code": "STORAGE_POOL_LIMIT_EXCEEDED",
            },
        )


def check_quota_available(user, needed_bytes: int):
    """
    Checks that the user has an active subscription, sufficient storage quota,
    that the file fits the plan's maximum file size, and that the global
    storage pool capacity is not exceeded.
    """
    check_storage_pool_capacity(needed_bytes)

    subscription = getattr(user, "subscription", None)
    if not subscription or not subscription.is_valid:
        raise SubscriptionRequiredException(
            detail={
                "error": "subscription_required",
                "message": "Choose a plan to start uploading files.",
                "code": "SUBSCRIPTION_REQUIRED",
            }
        )

    if not subscription.can_upload:
        raise SubscriptionRequiredException(
            detail={
                "error": "account_in_grace_period",
                "message": "Your plan has expired. Renew it to upload new files; existing files can still be downloaded.",
                "code": "ACCOUNT_IN_GRACE_PERIOD",
            }
        )

    max_file_size = subscription.plan.max_file_size
    if max_file_size and needed_bytes > max_file_size:
        raise QuotaExceededException(
            bytes_needed=needed_bytes,
            detail={
                "error": "file_too_large",
                "message": f"This file is larger than your plan's {max_file_size // (1024 ** 3)} GB per-file limit.",
                "code": "FILE_TOO_LARGE",
            },
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


def delete_spacebyte_entries_for_nodes(nodes, delete_forever: bool = False) -> int:
    """Best-effort trash or permanent delete of SpaceByte FileEntries for the given Nodes."""
    entry_ids = [n.spacebyte_entry_id for n in nodes if getattr(n, "spacebyte_entry_id", None)]
    if not entry_ids:
        return 0
    try:
        sb_client = get_spacebyte_client()
        if not sb_client.is_configured:
            logger.warning("SpaceByte not configured; skipping upstream delete for %s entries", len(entry_ids))
            return 0
        sb_client.delete_entries(entry_ids, delete_forever=delete_forever)
        return len(entry_ids)
    except Exception as e:
        logger.error("SpaceByte delete_entries failed for %s ids: %s", len(entry_ids), e)
        return 0


def restore_spacebyte_entries_for_nodes(nodes) -> int:
    """Best-effort restore of trashed SpaceByte entries when a vault node is restored."""
    entry_ids = [n.spacebyte_entry_id for n in nodes if getattr(n, "spacebyte_entry_id", None)]
    if not entry_ids:
        return 0
    try:
        sb_client = get_spacebyte_client()
        if not sb_client.is_configured:
            return 0
        sb_client.restore_entries(entry_ids)
        return len(entry_ids)
    except Exception as e:
        logger.error("SpaceByte restore_entries failed: %s", e)
        return 0


def get_owned_folder(user, folder_id) -> Node:
    folder = Node.objects.filter(
        id=folder_id, owner=user, type=Node.TYPE_FOLDER, deleted_at__isnull=True, trashed_at__isnull=True
    ).first()
    if not folder:
        raise NotFound("Folder not found.")
    return folder


def create_folder(user, encrypted_name: str, name_nonce: str, parent_id: str | None = None) -> Node:
    parent = get_owned_folder(user, parent_id) if parent_id else None

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


def move_node(node: Node, user, parent_id) -> Node:
    """Moves a node into another folder, refusing moves into itself or its own subfolders."""
    if not parent_id:
        node.parent = None
        return node
    parent = get_owned_folder(user, parent_id)
    if parent.id == node.id:
        raise ValidationError("A folder cannot be moved into itself.")
    if node.type == Node.TYPE_FOLDER:
        descendant_ids = {n.id for n in get_node_descendants(node)}
        if parent.id in descendant_ids:
            raise ValidationError("A folder cannot be moved into one of its own subfolders.")
    node.parent = parent
    return node


def part_count_for(size_bytes: int, part_size: int) -> int:
    return max(1, math.ceil(size_bytes / part_size))


def expected_encrypted_part_size(upload: Upload, part_number: int) -> int:
    """Exact ciphertext length of a part implied by the declared plaintext file size."""
    total_parts = part_count_for(upload.expected_size_bytes, upload.part_size)
    if part_number < total_parts:
        return upload.part_size + GCM_TAG_BYTES
    return upload.expected_size_bytes - (total_parts - 1) * upload.part_size + GCM_TAG_BYTES


def init_multipart_upload(
    user,
    encrypted_name: str,
    name_nonce: str,
    size_bytes: int,
    parent_id: str | None = None,
    node_id: str | None = None,
) -> dict:
    """
    Opens a SpaceByte multipart upload. The browser sends every encrypted part through
    the relay endpoint; presigned upstream URLs stay on the server so the stored bytes
    always match the size that is charged against the quota.
    """
    check_quota_available(user, size_bytes)

    parent = get_owned_folder(user, parent_id) if parent_id else None
    if node_id and not Node.objects.filter(id=node_id, owner=user, type=Node.TYPE_FILE, deleted_at__isnull=True).exists():
        raise NotFound("File not found.")

    # SpaceByte docs recommend 20 MB parts. Persist part_size on FileVersion for decrypt.
    part_size = 32 * 1024 * 1024 if size_bytes > 50 * 1024 * 1024 * 1024 else 20 * 1024 * 1024
    num_parts = part_count_for(size_bytes, part_size)

    sb_client = get_spacebyte_client()
    try:
        sb_init = sb_client.init_multipart_upload(
            filename=f"vault_{user.id}_{uuid.uuid4().hex[:8]}.bin",
            mime="application/octet-stream",
            size=size_bytes + num_parts * GCM_TAG_BYTES,
            extension="bin",
            part_count=num_parts,
            # Signing thousands of URLs up front is slow and they would expire before
            # the later parts are sent; the rest are signed just in time (_part_url).
            sign_count=PART_SIGN_BATCH,
        )
    except SpaceByteError as e:
        logger.error("SpaceByte init multipart failed: %s", e)
        raise upstream_error("Storage provider is unavailable. Please try again in a moment.") from e

    presigned_urls = [
        {"part_number": p.get("partNumber", p.get("part_number", 1)), "url": p["url"]}
        for p in sb_init.get("presigned_urls", [])
    ]
    expires_at = timezone.now() + timedelta(hours=24)

    upload = Upload.objects.create(
        user=user,
        parent_id=parent.id if parent else None,
        node_id=node_id,
        upload_id=sb_init["upload_id"],
        object_key=sb_init["key"],
        spacebyte_upload_id=sb_init["upload_id"],
        spacebyte_key=sb_init["key"],
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
        "part_size": part_size,
        "total_parts": num_parts,
        "expires_at": expires_at.isoformat(),
    }


def _verified_parts(upload: Upload) -> list[dict]:
    """Checks every part was relayed with its exact expected size; returns them in order."""
    total_parts = part_count_for(upload.expected_size_bytes, upload.part_size)
    received = upload.received_parts or {}
    missing = [n for n in range(1, total_parts + 1) if str(n) not in received]
    if missing:
        raise ValidationError(f"Upload is incomplete: {len(missing)} part(s) were not received.")
    parts = []
    for n in range(1, total_parts + 1):
        info = received[str(n)]
        if int(info.get("size", -1)) != expected_encrypted_part_size(upload, n):
            raise ValidationError(f"Part {n} has an unexpected size. Please retry the upload.")
        parts.append({"PartNumber": n, "ETag": info.get("etag", "")})
    return parts


@transaction.atomic
def complete_multipart_upload(
    upload_id: str,
    user,
    wrapped_file_key: str,
    content_nonce: str,
    checksum: str = "",
) -> Node:
    """
    Commits multipart upload, creates/updates Node, creates FileVersion, and increments quota atomically.
    The size recorded is the size of the parts actually received, not a client-reported value.
    """
    upload = Upload.objects.select_for_update().filter(id=upload_id, user=user).first()
    if not upload:
        raise NotFound("Upload session not found.")
    if upload.status == Upload.STATUS_COMPLETED:
        return upload.node
    if upload.status != Upload.STATUS_UPLOADING:
        raise ValidationError("Upload session is not active.")

    relayed_parts = _verified_parts(upload)
    stored_bytes = sum(expected_encrypted_part_size(upload, p["PartNumber"]) for p in relayed_parts)
    file_size = stored_bytes - len(relayed_parts) * GCM_TAG_BYTES

    # Quota check again on completion with the verified size
    check_quota_available(user, file_size)

    sb_client = get_spacebyte_client()
    try:
        # Prefer authoritative ETags (and sizes, when reported) from SpaceByte.
        listed = sb_client.get_uploaded_parts(upload.spacebyte_upload_id, upload.spacebyte_key)
        if listed:
            sb_parts = sorted(listed, key=lambda x: x["PartNumber"])
            if len(sb_parts) != len(relayed_parts):
                raise upstream_error("Storage provider is missing some parts of this file. Please retry the upload.")
            for part in sb_parts:
                if "Size" in part and part["Size"] != expected_encrypted_part_size(upload, part["PartNumber"]):
                    raise upstream_error("Storage provider reported an unexpected part size. Please retry the upload.")
        else:
            sb_parts = relayed_parts
            if any(not p["ETag"] for p in sb_parts):
                raise upstream_error("Missing upload confirmation from the storage provider. Please retry the upload.")
        sb_client.complete_multipart_upload(upload.spacebyte_upload_id, upload.spacebyte_key, sb_parts)
        entry_res = sb_client.create_file_entry(
            filename=upload.spacebyte_key,
            client_name=f"vault_{upload.id}.bin",
            size=stored_bytes,
            client_mime="application/octet-stream",
            client_extension="bin",
        )
        spacebyte_entry = entry_res.get("fileEntry", {})
    except UpstreamStorageError:
        raise
    except Exception as e:
        # Do NOT create a vault record pointing at data that was never finalized upstream.
        logger.error("SpaceByte complete multipart/entry failed for upload %s: %s", upload.id, e)
        raise upstream_error("Storage provider could not finalize the upload. Please retry.") from e
    if not spacebyte_entry or not spacebyte_entry.get("hash"):
        raise upstream_error("Storage provider did not register the uploaded file. Please retry.")

    parent = None
    if upload.parent_id:
        parent = Node.objects.filter(id=upload.parent_id, owner=user, trashed_at__isnull=True).first()

    if upload.node:
        # New version of an existing file: it keeps its name and location.
        node = upload.node
        node.size_bytes = file_size
        node.spacebyte_entry_id = spacebyte_entry.get("id")
        node.spacebyte_hash = spacebyte_entry.get("hash", "")
        node.save()
    else:
        node = Node.objects.create(
            owner=user,
            parent=parent,
            type=Node.TYPE_FILE,
            encrypted_name=upload.encrypted_name,
            name_nonce=upload.name_nonce,
            size_bytes=file_size,
            spacebyte_entry_id=spacebyte_entry.get("id"),
            spacebyte_hash=spacebyte_entry.get("hash", ""),
        )

    last_version = FileVersion.objects.filter(node=node).order_by("-version_no").first()
    version_no = (last_version.version_no + 1) if last_version else 1

    FileVersion.objects.create(
        node=node,
        version_no=version_no,
        object_key=upload.object_key,
        spacebyte_file_name=upload.spacebyte_key,
        size_bytes=file_size,
        part_size=upload.part_size,
        wrapped_file_key=wrapped_file_key,
        content_nonce=content_nonce,
        checksum=checksum,
    )

    upload.status = Upload.STATUS_COMPLETED
    upload.node = node
    upload.save(update_fields=["status", "node"])

    recalculate_user_quota(user)

    AuditLog.objects.create(
        user=user,
        action="file.uploaded",
        target_type="node",
        target_id=str(node.id),
        metadata={"version": version_no, "size_bytes": file_size},
    )

    return node


def abort_multipart_upload(upload_id: str, user):
    upload = Upload.objects.filter(id=upload_id, user=user).first()
    if not upload:
        raise NotFound("Upload session not found.")

    if upload.status == Upload.STATUS_UPLOADING:
        try:
            get_spacebyte_client().abort_multipart_upload(upload.spacebyte_upload_id, upload.spacebyte_key)
        except Exception as e:
            logger.warning("SpaceByte abort failed for upload %s: %s", upload.id, e)
        upload.status = Upload.STATUS_ABORTED
        upload.save(update_fields=["status"])


# Part uploads stream straight through to storage, so a body can't be re-sent here;
# only connection failures (before any byte is read) are retried. The browser retries
# everything else.
upload_pool = urllib3.PoolManager(
    maxsize=32,
    blocksize=256 * 1024,
    timeout=urllib3.Timeout(connect=10.0, read=180.0),
    retries=urllib3.Retry(total=2, connect=2, read=0, status=0, other=0, redirect=0, backoff_factor=0.5),
)

# Presigned part URLs are signed in small batches just before use and reused for a few
# minutes, well inside the provider's expiry.
PART_SIGN_BATCH = 8
PART_URL_FRESH_SECONDS = 300
_part_urls: dict[tuple[str, int], tuple[str, float]] = {}
_part_urls_lock = threading.Lock()


def _part_url(upload: Upload, part_number: int) -> str | None:
    key = (str(upload.id), part_number)
    now = time.monotonic()
    with _part_urls_lock:
        hit = _part_urls.get(key)
    if hit and now - hit[1] < PART_URL_FRESH_SECONDS:
        return hit[0]
    # URLs signed when the session opened are still fresh for the first few minutes.
    if not hit and (timezone.now() - upload.created_at).total_seconds() < PART_URL_FRESH_SECONDS:
        for p in upload.parts if isinstance(upload.parts, list) else []:
            if isinstance(p, dict) and p.get("part_number") == part_number and p.get("url"):
                return p["url"]

    total = part_count_for(upload.expected_size_bytes, upload.part_size)
    numbers = list(range(part_number, min(total, part_number + PART_SIGN_BATCH - 1) + 1))
    try:
        signed = get_spacebyte_client().sign_part_urls(upload.spacebyte_upload_id, upload.spacebyte_key, numbers)
    except Exception as e:
        logger.warning("Could not sign part URLs %s-%s for upload %s: %s", numbers[0], numbers[-1], upload.id, e)
        return None
    stamp = time.monotonic()
    with _part_urls_lock:
        for n, url in signed.items():
            _part_urls[(str(upload.id), n)] = (url, stamp)
        # Drop stale entries so the cache stays small on a long-running server.
        if len(_part_urls) > 4096:
            for k in [k for k, (_, t) in _part_urls.items() if stamp - t > PART_URL_FRESH_SECONDS]:
                del _part_urls[k]
    return signed.get(part_number)


def _forget_part_url(upload: Upload, part_number: int):
    with _part_urls_lock:
        _part_urls.pop((str(upload.id), part_number), None)


class _PartStream:
    """File-like view of the incoming request body that counts bytes as storage reads them."""

    def __init__(self, source, length: int):
        self.source = source
        self.remaining = length

    def read(self, size: int = -1) -> bytes:
        if self.remaining <= 0:
            return b""
        size = self.remaining if size is None or size < 0 else min(size, self.remaining)
        chunk = self.source.read(min(size, 1024 * 1024))
        if not chunk:
            # The browser went away mid-part; abort the upstream PUT rather than send short.
            raise IncompletePartError()
        self.remaining -= len(chunk)
        return chunk


def relay_upload_part(upload: Upload, part_number: int, body, content_length: int) -> str:
    """
    Streams one encrypted part from the browser to storage as it arrives (no buffering),
    after checking its declared length against the file size, and records its ETag.
    `body` is a readable stream of exactly `content_length` bytes.
    """
    total_parts = part_count_for(upload.expected_size_bytes, upload.part_size)
    if part_number < 1 or part_number > total_parts:
        raise ValidationError(f"Part number must be between 1 and {total_parts}.")
    expected = expected_encrypted_part_size(upload, part_number)
    if content_length != expected:
        raise ValidationError(f"Part {part_number} must be exactly {expected} bytes (got {content_length}).")

    url = _part_url(upload, part_number)
    if not url:
        raise upstream_error(f"Could not prepare storage for part {part_number}. Please retry.")

    stream = _PartStream(body, expected)
    if "mockSign=valid" in url and settings.DEBUG:
        while stream.read(1024 * 1024):
            pass
        etag = f'"{part_number}"'
    else:
        try:
            resp = upload_pool.request(
                "PUT",
                url,
                body=stream,
                headers={"Content-Type": "application/octet-stream", "Content-Length": str(expected)},
                chunked=False,
            )
        except IncompletePartError:
            raise
        except Exception as e:
            if isinstance(getattr(e, "reason", None), IncompletePartError) or isinstance(e.__cause__, IncompletePartError):
                raise IncompletePartError() from e
            _forget_part_url(upload, part_number)
            logger.error("Relay upload failed for part %s of upload %s: %s", part_number, upload.id, e)
            raise upstream_error(f"Could not send part {part_number} to storage. Please retry.") from e
        if resp.status not in (200, 201, 204):
            # Expired or rejected URL: sign a fresh one on the next attempt.
            _forget_part_url(upload, part_number)
            logger.error("Upstream returned HTTP %s for part %s of upload %s: %s", resp.status, part_number, upload.id, resp.data[:200])
            raise upstream_error(f"Storage rejected part {part_number} (HTTP {resp.status}). Please retry.")
        etag = (resp.headers.get("ETag") or "").strip()
    if stream.remaining:
        raise IncompletePartError()

    with transaction.atomic():
        locked = Upload.objects.select_for_update().get(id=upload.id)
        received = dict(locked.received_parts or {})
        received[str(part_number)] = {"etag": etag, "size": expected}
        locked.received_parts = received
        locked.save(update_fields=["received_parts"])
    return etag


def get_download_info(node: Node, user, version_no: int | None = None) -> dict:
    """
    Returns the authenticated stream URL for a file together with its wrapped file key,
    nonce and part size so the browser can decrypt it.
    """
    if node.owner_id != user.id:
        raise PermissionDenied("You do not have permission to access this file.")
    if node.type != Node.TYPE_FILE:
        raise NotFound("Folders cannot be downloaded directly.")

    versions = FileVersion.objects.filter(node=node)
    version = versions.filter(version_no=version_no).first() if version_no else versions.order_by("-version_no").first()
    if not version:
        raise NotFound("File version not found.")

    if version.part_size:
        part_size = version.part_size
    elif version.size_bytes > 5 * 1024 * 1024 * 1024:
        part_size = 16 * 1024 * 1024
    else:
        part_size = 8 * 1024 * 1024

    stream_url = f"/api/v1/nodes/{node.id}/content" + (f"?v={version.version_no}" if version_no else "")

    return {
        "node_id": str(node.id),
        "version_no": version.version_no,
        "size_bytes": version.size_bytes,
        "part_size": part_size,
        "wrapped_file_key": version.wrapped_file_key,
        "content_nonce": version.content_nonce,
        "download_url": stream_url,
    }


def get_node_descendants(node: Node) -> list[Node]:
    """Return all active descendant nodes (children, grandchildren, etc.)."""
    descendants = []
    seen = {node.id}
    current_parents = [node.id]
    while current_parents:
        children = [
            c for c in Node.objects.filter(parent_id__in=current_parents, deleted_at__isnull=True)
            if c.id not in seen
        ]
        if not children:
            break
        descendants.extend(children)
        seen.update(c.id for c in children)
        current_parents = [c.id for c in children]
    return descendants


def recalculate_user_quota(user) -> StorageQuota:
    """
    Recalculates actual bytes used across all active (non-trashed, non-deleted) files for the user.
    Synchronizes bytes_limit with active subscription plan if available.
    """
    quota, _ = StorageQuota.objects.get_or_create(user=user)
    active_bytes = (
        Node.objects.filter(
            owner=user,
            type=Node.TYPE_FILE,
            trashed_at__isnull=True,
            deleted_at__isnull=True,
        ).aggregate(total=models.Sum("size_bytes"))["total"]
        or 0
    )
    quota.bytes_used = max(0, active_bytes)

    subscription = getattr(user, "subscription", None)
    if subscription and subscription.plan and subscription.is_valid:
        if subscription.plan.storage_bytes and quota.bytes_limit != subscription.plan.storage_bytes:
            quota.bytes_limit = subscription.plan.storage_bytes

    quota.save(update_fields=["bytes_used", "bytes_limit"])
    return quota
