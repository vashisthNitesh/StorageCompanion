from rest_framework import serializers

from apps.links.models import ShareLink
from apps.links.services import EXPIRY_CHOICES

HEX_256 = r"^[0-9a-f]{64}$"


class SharePasswordSerializer(serializers.Serializer):
    salt = serializers.RegexField(r"^[0-9a-f]{32}$")
    kdf_params = serializers.JSONField()
    auth_hash = serializers.RegexField(HEX_256)


class ShareCreateSerializer(serializers.Serializer):
    expires_in = serializers.ChoiceField(choices=list(EXPIRY_CHOICES))
    max_downloads = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=10000)
    allow_download = serializers.BooleanField(default=True)
    version_no = serializers.IntegerField(required=False, min_value=1)
    wrapped_key = serializers.CharField(max_length=512)
    encrypted_name = serializers.CharField(max_length=4096)
    name_nonce = serializers.CharField(max_length=64)
    owner_wrapped_link_key = serializers.CharField(max_length=512)
    password = SharePasswordSerializer(required=False, allow_null=True)


class ShareLinkSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = ShareLink
        fields = [
            "id",
            "token",
            "created_at",
            "expires_at",
            "max_downloads",
            "download_count",
            "allow_download",
            "password_protected",
            "revoked_at",
            "last_accessed_at",
            "owner_wrapped_link_key",
            "status",
        ]
        read_only_fields = fields
