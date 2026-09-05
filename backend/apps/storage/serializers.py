from rest_framework import serializers
from apps.storage.models import Node, FileVersion, StorageQuota


class FileVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileVersion
        fields = [
            "id",
            "version_no",
            "size_bytes",
            "wrapped_file_key",
            "content_nonce",
            "checksum",
            "created_at",
        ]
        read_only_fields = fields


class NodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = [
            "id",
            "parent",
            "type",
            "encrypted_name",
            "name_nonce",
            "size_bytes",
            "thumbnail_object_key",
            "thumbnail_nonce",
            "created_at",
            "updated_at",
            "trashed_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CreateFolderSerializer(serializers.Serializer):
    parent = serializers.UUIDField(required=False, allow_null=True)
    encrypted_name = serializers.CharField()
    name_nonce = serializers.CharField(max_length=64)


class UpdateNodeSerializer(serializers.Serializer):
    encrypted_name = serializers.CharField(required=False)
    name_nonce = serializers.CharField(required=False, max_length=64)
    parent = serializers.UUIDField(required=False, allow_null=True)


class InitUploadSerializer(serializers.Serializer):
    parent_id = serializers.UUIDField(required=False, allow_null=True)
    node_id = serializers.UUIDField(required=False, allow_null=True)
    encrypted_name = serializers.CharField()
    name_nonce = serializers.CharField(max_length=64)
    size_bytes = serializers.IntegerField(min_value=1)


class PartSerializer(serializers.Serializer):
    part_number = serializers.IntegerField(min_value=1)
    etag = serializers.CharField(required=False, default="")


class CompleteUploadSerializer(serializers.Serializer):
    parts = serializers.ListField(child=serializers.DictField())
    wrapped_file_key = serializers.CharField()
    content_nonce = serializers.CharField(max_length=64)
    checksum = serializers.CharField(required=False, allow_blank=True, default="")
    thumbnail_object_key = serializers.CharField(required=False, allow_blank=True, default="")
    thumbnail_nonce = serializers.CharField(required=False, allow_blank=True, default="")


class StorageQuotaSerializer(serializers.ModelSerializer):
    bytes_remaining = serializers.IntegerField(read_only=True)
    percent_used = serializers.FloatField(read_only=True)

    class Meta:
        model = StorageQuota
        fields = [
            "bytes_used",
            "bytes_limit",
            "bytes_remaining",
            "percent_used",
            "updated_at",
        ]
        read_only_fields = fields
