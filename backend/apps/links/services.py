"""
Public file links. The browser wraps the file key with a random link key that travels only in
the URL fragment (#…), optionally combined with a key derived from a password. The server stores
wrapped blobs and enforces expiry, revocation and the download limit.
"""
import hashlib
import hmac
import secrets
from datetime import timedelta

from django.core import signing
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, NotFound, ValidationError

from apps.audit.models import AuditLog
from apps.links.models import ShareLink
from apps.storage.models import FileVersion, Node

EXPIRY_CHOICES = {
    "1h": timedelta(hours=1),
    "1d": timedelta(days=1),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "never": None,
}
MAX_ACTIVE_LINKS_PER_FILE = 50
GRANT_SALT = "links.content-grant"
# Long enough to stream a large video; revocation still applies to every request.
GRANT_MAX_AGE = 6 * 60 * 60
MAX_PASSWORD_ATTEMPTS = 10
PASSWORD_WINDOW_SECONDS = 15 * 60


class ShareUnavailable(APIException):
    """Why a link can't be used. `code` lets the public page show a specific message."""
    status_code = 410

    MESSAGES = {
        ShareLink.STATUS_EXPIRED: "This link has expired.",
        ShareLink.STATUS_REVOKED: "This link was turned off by its owner.",
        ShareLink.STATUS_LIMIT_REACHED: "This link has reached its download limit.",
        ShareLink.STATUS_UNAVAILABLE: "This file is no longer available.",
    }

    def __init__(self, status: str):
        super().__init__(detail={"error": self.MESSAGES[status], "code": f"SHARE_{status.upper()}"})


class WrongSharePassword(APIException):
    status_code = 403
    default_detail = {"error": "That password isn't right.", "code": "SHARE_WRONG_PASSWORD"}


class TooManySharePasswordAttempts(APIException):
    status_code = 429
    default_detail = {"error": "Too many wrong passwords. Try again in 15 minutes.", "code": "SHARE_PASSWORD_LOCKED"}


def new_token() -> str:
    return secrets.token_urlsafe(18)


def latest_version(node: Node) -> FileVersion | None:
    return node.versions.order_by("-version_no").first()


@transaction.atomic
def create_share(user, node: Node, data: dict) -> ShareLink:
    if node.owner_id != user.id or node.deleted_at:
        raise NotFound("File not found.")
    if node.type != Node.TYPE_FILE:
        raise ValidationError("Only files can be shared.")
    if node.trashed_at:
        raise ValidationError("Restore this file from the trash to share it.")
    version = latest_version(node)
    if version is None or (data.get("version_no") and data["version_no"] != version.version_no):
        raise ValidationError("This file changed. Refresh and try again.")
    active = ShareLink.objects.filter(file=node, revoked_at__isnull=True).exclude(expires_at__lte=timezone.now()).count()
    if active >= MAX_ACTIVE_LINKS_PER_FILE:
        raise ValidationError("This file has too many active links. Turn some off first.")

    expiry = EXPIRY_CHOICES[data["expires_in"]]
    password = data.get("password") or None
    link = ShareLink.objects.create(
        token=new_token(),
        file=node,
        version=version,
        created_by=user,
        expires_at=timezone.now() + expiry if expiry else None,
        max_downloads=data.get("max_downloads"),
        allow_download=data.get("allow_download", True),
        wrapped_key=data["wrapped_key"],
        encrypted_name=data["encrypted_name"],
        name_nonce=data["name_nonce"],
        owner_wrapped_link_key=data["owner_wrapped_link_key"],
        password_protected=bool(password),
        password_salt=password["salt"] if password else "",
        password_kdf_params=password["kdf_params"] if password else {},
        password_auth_hash=password["auth_hash"] if password else "",
    )
    AuditLog.objects.create(
        user=user,
        action="share.created",
        target_type="node",
        target_id=str(node.id),
        metadata={"link": str(link.id), "expires_in": data["expires_in"], "password": bool(password), "max_downloads": link.max_downloads},
    )
    return link


def revoke_share(user, link_id) -> ShareLink:
    link = ShareLink.objects.filter(id=link_id, created_by=user, file__owner=user).first()
    if link is None:
        raise NotFound("Link not found.")
    if not link.revoked_at:
        link.revoked_at = timezone.now()
        link.save(update_fields=["revoked_at"])
        AuditLog.objects.create(user=user, action="share.revoked", target_type="node", target_id=str(link.file_id), metadata={"link": str(link.id)})
    return link


def _link_or_404(token: str, *, lock: bool = False) -> ShareLink:
    qs = ShareLink.objects.select_related("file", "file__owner", "version")
    if lock:
        qs = qs.select_for_update(of=("self",))
    link = qs.filter(token=token).first()
    if link is None:
        raise NotFound({"error": "This link doesn't exist. Check that you copied all of it.", "code": "SHARE_NOT_FOUND"})
    return link


def _ensure_usable(link: ShareLink, *, counting: bool) -> None:
    state = link.status
    if state == ShareLink.STATUS_ACTIVE:
        return
    # Someone who already opened the link may keep streaming after the limit is reached.
    if state == ShareLink.STATUS_LIMIT_REACHED and not counting:
        return
    raise ShareUnavailable(state)


def _attempts_key(link: ShareLink) -> str:
    return f"share-pw-fail:{link.id}"


def _check_password(link: ShareLink, proof: str) -> None:
    if not link.password_protected:
        return
    key = _attempts_key(link)
    if cache.get(key, 0) >= MAX_PASSWORD_ATTEMPTS:
        raise TooManySharePasswordAttempts()
    ok = False
    if isinstance(proof, str) and len(proof) == 64:
        try:
            ok = hmac.compare_digest(hashlib.sha256(bytes.fromhex(proof)).hexdigest(), link.password_auth_hash)
        except ValueError:
            ok = False
    if not ok:
        if not cache.add(key, 1, PASSWORD_WINDOW_SECONDS):
            try:
                cache.incr(key)
            except ValueError:
                cache.set(key, 1, PASSWORD_WINDOW_SECONDS)
        raise WrongSharePassword()


def public_info(token: str) -> dict:
    """What the public page shows before anything is opened. Doesn't count as a download."""
    link = _link_or_404(token)
    _ensure_usable(link, counting=True)
    info = {
        "size_bytes": link.version.size_bytes,
        "allow_download": link.allow_download,
        "password_protected": link.password_protected,
        "expires_at": link.expires_at,
        "downloads_left": None if link.max_downloads is None else max(0, link.max_downloads - link.download_count),
    }
    if link.password_protected:
        info.update({"password_salt": link.password_salt, "password_kdf_params": link.password_kdf_params})
    else:
        info.update({"wrapped_key": link.wrapped_key, "encrypted_name": link.encrypted_name, "name_nonce": link.name_nonce})
    return info


def open_share(token: str, password_proof: str = "") -> dict:
    """
    Opens the link: checks the password, counts one download against the limit and returns a
    short-lived grant for the encrypted content. Expiry, revocation and the limit are checked
    under a row lock, so concurrent opens can't exceed the limit.
    """
    with transaction.atomic():
        link = _link_or_404(token, lock=True)
        _ensure_usable(link, counting=True)
        _check_password(link, password_proof)
        link.download_count += 1
        link.last_accessed_at = timezone.now()
        link.save(update_fields=["download_count", "last_accessed_at"])
    cache.delete(_attempts_key(link))
    AuditLog.objects.create(
        user=link.file.owner,
        action="share.opened",
        target_type="node",
        target_id=str(link.file_id),
        metadata={"link": str(link.id), "count": link.download_count},
    )
    version = link.version
    return {
        "grant": signing.dumps({"l": str(link.id)}, salt=GRANT_SALT),
        "wrapped_key": link.wrapped_key,
        "encrypted_name": link.encrypted_name,
        "name_nonce": link.name_nonce,
        "content_nonce": version.content_nonce,
        "part_size": version.part_size or (16 * 1024 * 1024 if version.size_bytes > 5 * 1024**3 else 8 * 1024 * 1024),
        "size_bytes": version.size_bytes,
        "allow_download": link.allow_download,
        "content_url": f"/api/v1/s/{link.token}/content",
    }


def link_for_grant(token: str, grant: str) -> ShareLink:
    """The link a content request may read, if its grant is valid and the link still works."""
    try:
        payload = signing.loads(grant or "", salt=GRANT_SALT, max_age=GRANT_MAX_AGE)
    except signing.BadSignature as err:
        raise ShareUnavailable(ShareLink.STATUS_EXPIRED) from err
    link = _link_or_404(token)
    if str(link.id) != payload.get("l"):
        raise NotFound({"error": "This link doesn't exist.", "code": "SHARE_NOT_FOUND"})
    _ensure_usable(link, counting=False)
    return link
