from rest_framework import serializers
from django.contrib.auth import authenticate
from apps.accounts.models import User, Session, MFADevice


class UserSerializer(serializers.ModelSerializer):
    subscription = serializers.SerializerMethodField()
    quota = serializers.SerializerMethodField()

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
            "email_verified_at",
            "mfa_enabled",
            "created_at",
            "subscription",
            "quota",
        ]
        read_only_fields = [
            "id",
            "is_staff",
            "is_superuser",
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
        try:
            subscription = getattr(obj, "subscription", None)
        except Exception:
            subscription = None

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

        if not quota:
            return {
                "bytes_used": 0,
                "bytes_limit": 0,
                "percent_used": 0,
            }

        return {
            "bytes_used": quota.bytes_used,
            "bytes_limit": quota.bytes_limit,
            "percent_used": quota.percent_used,
        }


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=10)
    full_name = serializers.CharField(required=False, allow_blank=True, default="")
    wrapped_master_key = serializers.CharField()
    kdf_salt = serializers.CharField()
    kdf_params = serializers.JSONField()
    public_key = serializers.CharField()
    wrapped_private_key = serializers.CharField()
    recovery_wrapped_master_key = serializers.CharField()

    def validate_email(self, value):
        email = value.lower().strip()
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("An account with this email address already exists.")
        return email


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(write_only=True)
    totp_code = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        raw_identifier = attrs.get("email", "").strip()
        password = attrs.get("password", "")

        # Support username like 'nitesh-vashisth' or full email
        lookup_email = raw_identifier.lower()
        if "@" not in raw_identifier:
            matched = (
                User.objects.filter(email__iexact=raw_identifier).first()
                or User.objects.filter(email__istartswith=f"{raw_identifier}@").first()
            )
            if matched:
                lookup_email = matched.email

        user = authenticate(username=lookup_email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("Account is inactive.")

        attrs["user"] = user
        return attrs


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
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=10)
    new_wrapped_master_key = serializers.CharField()
    new_kdf_salt = serializers.CharField()
    new_kdf_params = serializers.JSONField()


class RecoverySerializer(serializers.Serializer):
    email = serializers.EmailField()
    recovery_token_or_phrase = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=10)
    new_wrapped_master_key = serializers.CharField()
    new_kdf_salt = serializers.CharField()
    new_kdf_params = serializers.JSONField()
