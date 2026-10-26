from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel


class ShareLink(BaseModel):
    """
    A public link to one file. The file key is wrapped with a key that only exists in the
    link's URL fragment (and, optionally, a password), so the server can't decrypt the file.
    """

    STATUS_ACTIVE = "active"
    STATUS_EXPIRED = "expired"
    STATUS_REVOKED = "revoked"
    STATUS_LIMIT_REACHED = "limit_reached"
    STATUS_UNAVAILABLE = "unavailable"

    token = models.CharField(max_length=64, unique=True)
    file = models.ForeignKey("storage.Node", on_delete=models.CASCADE, related_name="share_links")
    # The version whose file key is wrapped; a newer upload makes the link stale.
    version = models.ForeignKey("storage.FileVersion", on_delete=models.CASCADE, related_name="share_links")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="share_links")
    expires_at = models.DateTimeField(null=True, blank=True)
    max_downloads = models.PositiveIntegerField(null=True, blank=True)
    download_count = models.PositiveIntegerField(default=0)
    allow_download = models.BooleanField(default=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_accessed_at = models.DateTimeField(null=True, blank=True)

    # File key wrapped with the link key (combined with the password key when there is one).
    wrapped_key = models.TextField()
    # File name encrypted with the same key, for the recipient.
    encrypted_name = models.TextField()
    name_nonce = models.CharField(max_length=64)
    # The link key wrapped with the owner's master key, so the owner can copy the link again.
    owner_wrapped_link_key = models.TextField()

    password_protected = models.BooleanField(default=False)
    password_salt = models.CharField(max_length=64, blank=True, default="")
    password_kdf_params = models.JSONField(default=dict, blank=True)
    # SHA-256 of a proof derived from the password in the browser.
    password_auth_hash = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["file", "revoked_at"])]

    def __str__(self):
        return f"Share {self.token[:6]}… of {self.file_id}"

    @property
    def status(self) -> str:
        if self.revoked_at:
            return self.STATUS_REVOKED
        if self.expires_at and timezone.now() >= self.expires_at:
            return self.STATUS_EXPIRED
        if self.max_downloads is not None and self.download_count >= self.max_downloads:
            return self.STATUS_LIMIT_REACHED
        node = self.file
        if node.trashed_at or node.deleted_at or not node.owner.is_active:
            return self.STATUS_UNAVAILABLE
        latest_id = node.versions.order_by("-version_no").values_list("id", flat=True).first()
        if latest_id != self.version_id:
            return self.STATUS_UNAVAILABLE
        return self.STATUS_ACTIVE
