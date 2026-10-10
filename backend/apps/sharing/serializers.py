from rest_framework import serializers

from apps.sharing.models import Share
from apps.storage.serializers import NodeSerializer


class ShareSerializer(serializers.ModelSerializer):
    node_details = NodeSerializer(source="node", read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    has_password = serializers.SerializerMethodField()

    class Meta:
        model = Share
        fields = [
            "id",
            "node",
            "node_details",
            "type",
            "recipient",
            "wrapped_key",
            "permission",
            "has_password",
            "expires_at",
            "max_downloads",
            "download_count",
            "is_active",
            "created_at",
            "revoked_at",
        ]
        read_only_fields = ["id", "created_by", "download_count", "created_at", "revoked_at"]

    def get_has_password(self, obj):
        return obj.password_hash is not None


class CreateShareSerializer(serializers.Serializer):
    node_id = serializers.UUIDField()
    type = serializers.ChoiceField(choices=Share.TYPE_CHOICES)
    recipient_email = serializers.EmailField(required=False, allow_blank=True)
    wrapped_key = serializers.CharField()
    permission = serializers.ChoiceField(choices=Share.PERM_CHOICES, default=Share.PERM_DOWNLOAD)
    require_password = serializers.BooleanField(required=False, default=False)
    password = serializers.CharField(required=False, allow_blank=True)
    expires_at = serializers.DateTimeField(required=False, allow_null=True)
    max_downloads = serializers.IntegerField(required=False, allow_null=True, min_value=1)

    def validate(self, attrs):
        require_pw = attrs.get("require_password", False)
        pw = attrs.get("password")
        if require_pw and (not pw or len(pw.strip()) < 4):
            raise serializers.ValidationError(
                {"password": "A password of at least 4 characters is required when password protection is enabled."}
            )
        return attrs


class PublicShareAuthSerializer(serializers.Serializer):
    password = serializers.CharField()
