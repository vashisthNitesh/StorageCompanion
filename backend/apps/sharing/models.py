import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.common.models import BaseModel
from apps.storage.models import Node


class Share(BaseModel):
    TYPE_LINK = "link"
    TYPE_USER = "user"
    TYPE_CHOICES = [
        (TYPE_LINK, "Public Link"),
        (TYPE_USER, "User to User"),
    ]

    PERM_VIEW = "view"
    PERM_DOWNLOAD = "download"
    PERM_EDIT = "edit"
    PERM_CHOICES = [
        (PERM_VIEW, "View Only"),
        (PERM_DOWNLOAD, "View & Download"),
        (PERM_EDIT, "Edit / Upload"),
    ]

    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name="shares",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_shares",
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="received_shares",
    )
    
    # Encrypted File Key (wrapped with recipient's public key or ephemeral link key)
    wrapped_key = models.TextField()
    
    # SHA-256 hash of the public link token (token itself is never stored plain)
    link_token_hash = models.CharField(max_length=64, blank=True, db_index=True)
    
    permission = models.CharField(max_length=20, choices=PERM_CHOICES, default=PERM_DOWNLOAD)
    password_hash = models.CharField(max_length=255, null=True, blank=True)
    
    expires_at = models.DateTimeField(null=True, blank=True)
    max_downloads = models.IntegerField(null=True, blank=True)
    download_count = models.IntegerField(default=0)
    revoked_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_active(self):
        if self.revoked_at is not None:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        if self.max_downloads and self.download_count >= self.max_downloads:
            return False
        return True

    def __str__(self):
        return f"Share({self.id}, node={self.node_id}, type={self.type}, active={self.is_active})"
