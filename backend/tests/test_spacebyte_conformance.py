"""SpaceByte OpenAPI conformance + large-file/purge behaviour (mock client, no network)."""
from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from apps.billing.services import purge_user_vault_data
from apps.storage.models import FileVersion, Node, Upload
from apps.storage.services import (
    complete_multipart_upload,
    init_multipart_upload,
)
from apps.storage.spacebyte import SpaceByteClient


@pytest.mark.django_db
def test_multipart_create_sends_required_spec_fields(monkeypatch):
    captured = {}

    def fake_request(self, method, path, data=None, params=None, timeout=15):
        if "create" in path and "multipart" in path:
            captured["create"] = data
            return {"status": "success", "uploadId": "up1", "key": "uploads/u/file.bin", "acl": "private"}
        if "batch-sign" in path:
            return {"status": "success", "urls": [{"partNumber": 1, "url": "https://example/p1"}]}
        return {"status": "success"}

    monkeypatch.setattr(SpaceByteClient, "_request", fake_request)
    client = SpaceByteClient(access_token="tok_test")
    assert client.is_configured
    res = client.init_multipart_upload(
        "vault.bin", "application/octet-stream", size=12345, extension="bin", part_count=1
    )
    assert res["upload_id"] == "up1"
    body = captured["create"]
    assert body["filename"] == "vault.bin"
    assert body["mime"] == "application/octet-stream"
    assert body["size"] == 12345
    assert body["extension"] == "bin"


@pytest.mark.django_db
def test_create_file_entry_uses_basename_and_string_delete_payload(monkeypatch):
    captured = {}

    def fake_request(self, method, path, data=None, params=None, timeout=15):
        captured[path] = {"method": method, "data": data}
        if path == "s3/entries":
            return {"status": "success", "fileEntry": {"id": 9, "hash": "abcHash"}}
        return {"status": "success"}

    monkeypatch.setattr(SpaceByteClient, "_request", fake_request)
    client = SpaceByteClient(access_token="tok_test")
    client.create_file_entry(
        filename="uploads/user/vault_x.bin",
        client_name="vault_x.bin",
        size=100,
        client_mime="application/octet-stream",
        client_extension="bin",
    )
    assert captured["s3/entries"]["data"]["filename"] == "vault_x.bin"
    client.delete_entries([9, 10], delete_forever=True)
    assert captured["file-entries"]["method"] == "DELETE"
    assert captured["file-entries"]["data"]["entryIds"] == ["9", "10"]
    assert captured["file-entries"]["data"]["deleteForever"] == "true"


@pytest.mark.django_db
def test_init_upload_uses_20mb_parts_and_persists_part_size(subscribed_user, settings):
    settings.SPACEBYTE_ACCESS_TOKEN = ""  # force local S3/mock path
    size = 25 * 1024 * 1024  # > 20 MiB → 2 parts
    info = init_multipart_upload(
        subscribed_user,
        encrypted_name="ZW5j",
        name_nonce="aabbccddeeff001122334455",
        size_bytes=size,
    )
    assert info["part_size"] == 20 * 1024 * 1024
    assert info["total_parts"] == 2
    node = complete_multipart_upload(
        info["upload_session_id"],
        subscribed_user,
        parts=[{"part_number": 1, "etag": '"e1"'}, {"part_number": 2, "etag": '"e2"'}],
        wrapped_file_key="wrapped",
        content_nonce="00112233445566778899aabb",
    )
    ver = FileVersion.objects.get(node=node)
    assert ver.part_size == 20 * 1024 * 1024


@pytest.mark.django_db
def test_spacebyte_complete_prefers_get_uploaded_parts(subscribed_user, monkeypatch):
    upload = Upload.objects.create(
        user=subscribed_user,
        upload_id="sb-up",
        object_key="uploads/u/k.bin",
        spacebyte_upload_id="sb-up",
        spacebyte_key="uploads/u/k.bin",
        encrypted_name="ZW5j",
        name_nonce="n",
        expected_size_bytes=100,
        part_size=20 * 1024 * 1024,
        status=Upload.STATUS_UPLOADING,
        expires_at=timezone.now() + timedelta(hours=1),
    )

    calls = []

    class FakeSB:
        is_configured = True

        def get_uploaded_parts(self, upload_id, key):
            calls.append("list")
            return [{"PartNumber": 1, "ETag": '"real"'}]

        def complete_multipart_upload(self, upload_id, key, parts):
            calls.append(("complete", parts))
            return {"status": "success"}

        def create_file_entry(self, **kw):
            calls.append(("entry", kw["filename"]))
            return {"fileEntry": {"id": 42, "hash": "h42"}}

    monkeypatch.setattr("apps.storage.services.get_spacebyte_client", lambda: FakeSB())
    node = complete_multipart_upload(
        str(upload.id),
        subscribed_user,
        parts=[{"part_number": 1, "etag": ""}],  # empty client etag — must use listed
        wrapped_file_key="w",
        content_nonce="00",
    )
    assert ("complete", [{"PartNumber": 1, "ETag": '"real"'}]) in calls
    assert node.spacebyte_hash == "h42"
    assert FileVersion.objects.get(node=node).part_size == 20 * 1024 * 1024


@pytest.mark.django_db
def test_trash_and_purge_call_spacebyte_delete(subscribed_user, auth_client, monkeypatch):
    node = Node.objects.create(
        owner=subscribed_user,
        type=Node.TYPE_FILE,
        encrypted_name="ZQ==",
        name_nonce="n",
        size_bytes=10,
        spacebyte_entry_id=99,
        spacebyte_hash="hh",
    )
    FileVersion.objects.create(
        node=node,
        version_no=1,
        object_key="k-unique-trash-test",
        size_bytes=10,
        wrapped_file_key="w",
        content_nonce="00",
        part_size=8 * 1024 * 1024,
    )
    seen = []

    class FakeSB:
        is_configured = True

        def delete_entries(self, entry_ids, delete_forever=False):
            seen.append((list(entry_ids), delete_forever))
            return {"status": "success"}

        def restore_entries(self, entry_ids):
            seen.append(("restore", list(entry_ids)))
            return {"status": "success"}

    monkeypatch.setattr("apps.storage.services.get_spacebyte_client", lambda: FakeSB())

    res = auth_client.delete(f"/api/v1/nodes/{node.id}")
    assert res.status_code == 200
    assert seen[0][0] == [99]
    assert seen[0][1] is False

    res = auth_client.post(f"/api/v1/nodes/{node.id}/restore")
    assert res.status_code == 200
    assert seen[1][0] == "restore"

    seen.clear()
    deleted = purge_user_vault_data(subscribed_user)
    assert deleted >= 1
    assert seen and seen[0][1] is True
