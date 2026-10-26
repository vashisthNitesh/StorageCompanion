from rest_framework import serializers
from apps.accounts.models import User, Session

# 32-byte values the browser sends as lowercase hex (auth keys, recovery proofs and their hashes).
HEX_256 = r"^[0-9a-f]{64}$"


def hex_256(**kwargs):
    return serializers.RegexField(HEX_256, error_messages={"invalid": "Invalid key."}, **kwargs)


class UserSerializer(serializers.ModelSerializer):
    subscription = serializers.SerializerMethodField()
    quota = serializers.SerializerMethodField()
    has_google = serializers.SerializerMethodField()
    has_recovery_key = serializers.BooleanField(read_only=True)

    def get_has_google(self, obj):
        return bool(obj.google_sub)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "is_staff",
            "is_superuser",
            "wrapped_master_key",
            "kdf_salt",
            "kdf_params",
            "public_key",
            "wrapped_private_key",
            "recovery_wrapped_master_key",
            "has_recovery_key",
            "recovery_key_confirmed_at",
            "auth_scheme",
            "email_verified_at",
            "mfa_enabled",
            "has_google",
            "created_at",
            "subscription",
            "quota",
        ]
        read_only_fields = [
            "id",
            "is_staff",
            "is_superuser",
            "recovery_key_confirmed_at",
            "auth_scheme",
            "email_verified_at",
            "mfa_enabled",
            "created_at",
            "subscription",
            "quota",
        ]

    def get_subscription(self, obj):
        if obj.is_staff or obj.is_superuser:
            return {
                "has_active_subscription": True,
                "status": "admin",
                "plan_name": "Master Administrator (No Pack)",
                "plan_code": "admin",
            }
        from apps.billing.models import Subscription
        subscription = Subscription.objects.filter(user=obj).select_related("plan").first()

        if not subscription:
            return {
                "has_active_subscription": False,
                "status": "no_subscription",
                "plan_name": None,
                "plan_code": None,
            }

        return {
            "has_active_subscription": bool(subscription.is_valid),
            "status": subscription.status,
            "plan_name": subscription.plan.name if subscription.plan else None,
            "plan_code": subscription.plan.code if subscription.plan else None,
            "current_period_end": subscription.current_period_end.isoformat() if subscription.current_period_end else None,
            "grace_period_ends_at": subscription.grace_period_ends_at.isoformat() if subscription.grace_period_ends_at else None,
            "is_in_grace_period": bool(subscription.is_in_grace_period),
            "retention_days_remaining": subscription.retention_days_remaining,
            "days_until_expiration": subscription.days_until_expiration,
            "can_upload": bool(subscription.can_upload),
        }

    def get_quota(self, obj):
        if obj.is_staff or obj.is_superuser:
            return {
                "bytes_used": 0,
                "bytes_limit": 0,
                "percent_used": 0,
            }
        try:
            quota = getattr(obj, "storage_quota", None)
        except Exception:
            quota = None

        subscription = getattr(obj, "subscription", None)
        active_plan_limit = 0
        if subscription and subscription.plan and subscription.plan.storage_bytes:
            active_plan_limit = subscription.plan.storage_bytes

        bytes_limit = quota.bytes_limit if (quota and quota.bytes_limit) else active_plan_limit
        bytes_used = quota.bytes_used if quota else 0

        # If quota object exists but limit was 0, sync it with the active plan
        if quota and active_plan_limit > 0 and quota.bytes_limit != active_plan_limit:
            quota.bytes_limit = active_plan_limit
            try:
                quota.save(update_fields=["bytes_limit"])
            except Exception:
                pass
            bytes_limit = active_plan_limit

        percent_used = round((bytes_used / bytes_limit * 100), 2) if bytes_limit > 0 else 0

        return {
            "bytes_used": bytes_used,
            "bytes_limit": bytes_limit,
            "percent_used": percent_used,
        }


class RegisterSerializer(serializers.Serializer):
    """The browser sends a key derived from the password, never the password itself."""
    email = serializers.EmailField()
    auth_key = hex_256(write_only=True)
    full_name = serializers.CharField(required=False, allow_blank=True, default="")
    wrapped_master_key = serializers.CharField()
    kdf_salt = serializers.CharField()
    kdf_params = serializers.JSONField()
    public_key = serializers.CharField()
    wrapped_private_key = serializers.CharField()
    recovery_wrapped_master_key = serializers.CharField()
    recovery_auth_hash = hex_256()

    def validate_email(self, value):
        email = value.lower().strip()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("An account with this email address already exists.")
        return email


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    # Upgraded accounts send auth_key; staff and older accounts send password (plus auth_key
    # once, which upgrades the account).
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    auth_key = hex_256(write_only=True, required=False)
    totp_code = serializers.CharField(required=False, allow_blank=True)


class SessionSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = Session
        fields = [
            "id",
            "device_label",
            "ip_address",
            "user_agent",
            "last_seen",
            "created_at",
            "is_active",
        ]
        read_only_fields = fields


class ChangePasswordSerializer(serializers.Serializer):
    # Proof of the current secret: auth_key for upgraded accounts, password otherwise.
    current_auth_key = hex_256(write_only=True, required=False)
    current_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    # Vault accounts: the master key re-wrapped in the browser with the new password's KEK.
    new_auth_key = hex_256(write_only=True, required=False)
    new_wrapped_master_key = serializers.CharField(required=False, allow_blank=True, default="")
    new_kdf_salt = serializers.CharField(required=False, allow_blank=True, default="")
    new_kdf_params = serializers.JSONField(required=False, default=dict)
    # Accounts without a vault (staff) still set a plain password.
    new_password = serializers.CharField(write_only=True, required=False, min_length=10)


class GoogleAuthSerializer(serializers.Serializer):
    credential = serializers.CharField(required=True)
    totp_code = serializers.CharField(required=False, allow_blank=True)



class VaultSetupSerializer(serializers.Serializer):
    wrapped_master_key = serializers.CharField()
    kdf_salt = serializers.CharField()
    kdf_params = serializers.JSONField()
    public_key = serializers.CharField()
    wrapped_private_key = serializers.CharField()
    recovery_wrapped_master_key = serializers.CharField()
    recovery_auth_hash = hex_256()


class RecoveryKeySerializer(serializers.Serializer):
    recovery_wrapped_master_key = serializers.CharField()
    recovery_auth_hash = hex_256()


class PasswordResetCompleteSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    # "recovery": the master key re-wrapped with the new password, proven with the recovery key.
    # "reset": no recovery key; a brand-new vault replaces the old one (old files stay unreadable).
    mode = serializers.ChoiceField(choices=["recovery", "reset"])
    auth_key = hex_256(write_only=True)
    wrapped_master_key = serializers.CharField()
    kdf_salt = serializers.CharField()
    kdf_params = serializers.JSONField()
    recovery_auth = hex_256(write_only=True, required=False)
    public_key = serializers.CharField(required=False)
    wrapped_private_key = serializers.CharField(required=False)
    confirm_data_loss = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if attrs["mode"] == "recovery" and not attrs.get("recovery_auth"):
            raise serializers.ValidationError("Enter your recovery key.")
        if attrs["mode"] == "reset":
            if not attrs.get("confirm_data_loss"):
                raise serializers.ValidationError("Confirm that files uploaded before can't be decrypted.")
            if not attrs.get("public_key") or not attrs.get("wrapped_private_key"):
                raise serializers.ValidationError("Missing vault keys.")
        return attrs
