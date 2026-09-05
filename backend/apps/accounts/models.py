import uuid
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from apps.common.models import BaseModel, TimeStampedModel


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    email = models.EmailField(unique=True, db_index=True)
    full_name = models.CharField(max_length=255, blank=True, default="")
    
    # Zero-knowledge cryptographic metadata
    # Master key wrapped with client-side derived Key Encryption Key (KEK)
    wrapped_master_key = models.TextField(blank=True, default="")
    # Salt used for Argon2id KDF in client browser
    kdf_salt = models.CharField(max_length=255, blank=True, default="")
    # Argon2id parameters (e.g., {"m": 65536, "t": 3, "p": 4})
    kdf_params = models.JSONField(default=dict, blank=True)
    
    # Public X25519 key used by other users to encrypt shared file keys to this user
    public_key = models.TextField(blank=True, default="")
    # X25519 private key wrapped with user's Master Key
    wrapped_private_key = models.TextField(blank=True, default="")
    
    # Master key wrapped with the 24-word recovery phrase
    recovery_wrapped_master_key = models.TextField(blank=True, default="")
    
    # Verification & Security
    email_verified_at = models.DateTimeField(null=True, blank=True)
    mfa_enabled = models.BooleanField(default=False)
    
    # Staff / Status
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email


class MFADevice(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="mfa_devices")
    secret = models.CharField(max_length=128)  # TOTP base32 secret
    backup_codes = models.JSONField(default=list, blank=True)  # Hashed backup codes
    confirmed = models.BooleanField(default=False)
    device_name = models.CharField(max_length=100, default="Authenticator App")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"MFA Device for {self.user.email} ({self.device_name})"


class Session(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    token_jti = models.CharField(max_length=255, unique=True, db_index=True)
    device_label = models.CharField(max_length=255, default="Web Browser")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    last_seen = models.DateTimeField(default=timezone.now)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-last_seen"]

    @property
    def is_active(self):
        return self.revoked_at is None

    def __str__(self):
        return f"{self.user.email} - {self.device_label} ({self.ip_address})"
