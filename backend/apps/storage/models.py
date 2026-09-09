import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.common.models import BaseModel, TimeStampedModel


class StorageQuota(TimeStampedModel):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="storage_quota",
        primary_key=True,
    )
    bytes_used = models.BigIntegerField(default=0)
    bytes_limit = models.BigIntegerField(default=0)  # Determined by active subscription plan

    @property
    def bytes_remaining(self):
        return max(0, self.bytes_limit - self.bytes_used)

    @property
    def percent_used(self):
        if self.bytes_limit <= 0:
            return 100.0 if self.bytes_used > 0 else 0.0
        return min(100.0, round((self.bytes_used / self.bytes_limit) * 100, 2))

    @property
    def is_exceeded(self):
        return self.bytes_used > self.bytes_limit

    @classmethod
    def get_global_pool_stats(cls):
        """
        Returns aggregate stats for the 1 TB SpaceByte testing pool.
        """
        total_pool = getattr(settings, "SPACEBYTE_STORAGE_POOL_LIMIT_BYTES", 1000 * 1024 * 1024 * 1024)
        used_agg = cls.objects.aggregate(total=models.Sum("bytes_used"))["total"] or 0
        remaining = max(0, total_pool - used_agg)
        percent = round((used_agg / total_pool) * 100, 2) if total_pool > 0 else 100.0
        return {
            "total_pool_bytes": total_pool,
            "total_pool_gb": round(total_pool / (1024 * 1024 * 1024), 1),
            "used_bytes": used_agg,
            "used_gb": round(used_agg / (1024 * 1024 * 1024), 2),
            "remaining_bytes": remaining,
            "remaining_gb": round(remaining / (1024 * 1024 * 1024), 2),
            "percent_used": min(100.0, percent),
            "provider": "spacebyte",
            "is_pool_full": used_agg >= total_pool,
        }

    def __str__(self):
        return f"Quota for {self.user.email}: {self.bytes_used}/{self.bytes_limit} bytes ({self.percent_used}%)"


class Node(BaseModel):
    TYPE_FOLDER = "folder"
    TYPE_FILE = "file"
    TYPE_CHOICES = [
        (TYPE_FOLDER, "Folder"),
        (TYPE_FILE, "File"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="nodes",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    # Encrypted name ciphertext and nonce (AES-GCM client side)
    encrypted_name = models.TextField()
    name_nonce = models.CharField(max_length=64)
    size_bytes = models.BigIntegerField(default=0)
    # Thumbnail reference for client-side encrypted preview
    thumbnail_object_key = models.CharField(max_length=255, blank=True, default="")
    thumbnail_nonce = models.CharField(max_length=64, blank=True, default="")
    
    # SpaceByte upstream integration fields
    spacebyte_entry_id = models.BigIntegerField(null=True, blank=True, db_index=True)
    spacebyte_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)

    # Soft deletion & trashing
    trashed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["type", "-created_at"]
        indexes = [
            models.Index(fields=["owner", "parent", "trashed_at", "deleted_at"]),
        ]

    @property
    def is_trashed(self):
        return self.trashed_at is not None

    def __str__(self):
        return f"Node({self.id}, {self.type}, owner={self.owner_id})"


class FileVersion(BaseModel):
    node = models.ForeignKey(
        Node,
        on_delete=models.CASCADE,
        related_name="versions",
    )
    version_no = models.IntegerField(default=1)
    object_key = models.CharField(max_length=255, unique=True, db_index=True)
    size_bytes = models.BigIntegerField()
    # Encrypted File Key (wrapped with owner's Master Key)
    wrapped_file_key = models.TextField()
    content_nonce = models.CharField(max_length=64)
    checksum = models.CharField(max_length=128, blank=True, default="")
    spacebyte_file_name = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-version_no"]
        unique_together = ("node", "version_no")

    def __str__(self):
        return f"FileVersion(node={self.node_id}, v={self.version_no}, size={self.size_bytes})"


class Upload(BaseModel):
    STATUS_INITIATED = "initiated"
    STATUS_UPLOADING = "uploading"
    STATUS_COMPLETED = "completed"
    STATUS_ABORTED = "aborted"
    STATUS_CHOICES = [
        (STATUS_INITIATED, "Initiated"),
        (STATUS_UPLOADING, "Uploading"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_ABORTED, "Aborted"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploads",
    )
    node = models.ForeignKey(
        Node,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pending_uploads",
    )
    parent_id = models.UUIDField(null=True, blank=True)
    upload_id = models.CharField(max_length=255, db_index=True)
    object_key = models.CharField(max_length=255, unique=True)
    spacebyte_upload_id = models.CharField(max_length=255, blank=True, default="")
    spacebyte_key = models.CharField(max_length=255, blank=True, default="")
    encrypted_name = models.TextField()
    name_nonce = models.CharField(max_length=64)
    expected_size_bytes = models.BigIntegerField()
    part_size = models.IntegerField(default=8 * 1024 * 1024)  # 8 MB default chunk size
    parts = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_INITIATED)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Upload({self.id}, s3_upload_id={self.upload_id}, status={self.status})"
