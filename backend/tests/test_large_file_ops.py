from datetime import timedelta
from io import StringIO
from unittest import mock

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.storage.models import FileVersion, Node, Upload
from apps.storage.spacebyte import SpaceByteError


def test_configure_storage_cors_exposes_etag(fake_s3, settings):
    call_command("configure_storage_cors", "--origin", "https://app.example.com/", stdout=StringIO())
    rule = fake_s3.cors["CORSConfiguration"]["CORSRules"][0]
    assert rule["AllowedOrigins"] == ["https://app.example.com"]
    assert "PUT" in rule["AllowedMethods"] and "ETag" in rule["ExposeHeaders"]


@pytest.mark.django_db
def test_cleanup_stale_uploads_aborts_old_sessions(subscribed_user, fake_s3):
    aborted = []
    fake_s3.abort_multipart_upload = lambda **kw: aborted.append(kw["UploadId"]) or {}
    old = Upload.objects.create(user=subscribed_user, object_key="k1", upload_id="u-old", expected_size_bytes=1,
                                encrypted_name="e", name_nonce="n", expires_at=timezone.now(), status=Upload.STATUS_UPLOADING)
    Upload.objects.filter(id=old.id).update(created_at=timezone.now() - timedelta(days=3))
    Upload.objects.create(user=subscribed_user, object_key="k2", upload_id="u-new", expected_size_bytes=1,
                          encrypted_name="e", name_nonce="n", expires_at=timezone.now(), status=Upload.STATUS_UPLOADING)
    call_command("cleanup_stale_uploads", "--hours", "48", stdout=StringIO())
    assert aborted == ["u-old"]
    assert Upload.objects.get(id=old.id).status == Upload.STATUS_ABORTED
    assert Upload.objects.get(upload_id="u-new").status == Upload.STATUS_UPLOADING


def _sb_file(owner):
    node = Node.objects.create(owner=owner, type=Node.TYPE_FILE, encrypted_name="ZQ==", name_nonce="n",
                               size_bytes=10, spacebyte_hash="MTM2MTgwMTF8cA")
    FileVersion.objects.create(node=node, version_no=1, object_key="sb/key", size_bytes=10,
                               wrapped_file_key="w", content_nonce="00")
    return node


@pytest.mark.django_db
def test_download_info_never_returns_authenticated_spacebyte_api_url(auth_client, subscribed_user):
    node = _sb_file(subscribed_user)
    with mock.patch("apps.storage.spacebyte.SpaceByteClient.resolve_direct_download_url") as resolve:
        res = auth_client.get(f"/api/v1/nodes/{node.id}/download")
    assert res.status_code == 200
    assert res.data["direct_url"] is None
    assert res.data["download_url"] == f"/api/v1/nodes/{node.id}/content"
    resolve.assert_not_called()  # the ~11 s resolution is skipped unless enabled


@pytest.mark.django_db
def test_content_upstream_403_is_a_clean_error(auth_client, subscribed_user):
    node = _sb_file(subscribed_user)
    err = SpaceByteError("SpaceByte HTTP Error 403: <html>Forbidden</html>", status_code=403)
    with mock.patch("apps.storage.spacebyte.SpaceByteClient.download_stream", side_effect=err), \
            mock.patch("apps.storage.spacebyte.SpaceByteClient.is_configured", new_callable=mock.PropertyMock, return_value=True):
        res = auth_client.get(f"/api/v1/nodes/{node.id}/content")
    assert res.status_code == 502
    assert res.data["code"] == "upstream_forbidden"
    assert "<html>" not in res.data["error"]


@pytest.mark.django_db
def test_content_passes_range_to_spacebyte(auth_client, subscribed_user):
    import io

    node = _sb_file(subscribed_user)
    with mock.patch("apps.storage.spacebyte.SpaceByteClient.download_stream",
                    return_value=(io.BytesIO(b"abc"), 206, {"Content-Range": "bytes 0-2/10", "Content-Length": "3"})) as ds:
        res = auth_client.get(f"/api/v1/nodes/{node.id}/content", HTTP_RANGE="bytes=0-2")
    assert res.status_code == 206
    assert ds.call_args.kwargs["range_header"] == "bytes=0-2"
    assert res["Content-Range"] == "bytes 0-2/10"
