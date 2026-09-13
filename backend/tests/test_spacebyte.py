import pytest
from django.conf import settings
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.billing.models import Plan, Subscription
from apps.storage.models import StorageQuota
from apps.storage.spacebyte import SpaceByteClient, get_spacebyte_client
from apps.storage.services import check_storage_pool_capacity, QuotaExceededException


@pytest.mark.django_db
def test_spacebyte_client_methods():
    client = SpaceByteClient(base_url="https://spacebyte.in/api/v1", access_token="")
    assert not client.is_configured

    # Test multipart initialization mock
    init_res = client.init_multipart_upload("test-file.bin", "application/octet-stream", part_count=3)
    assert "upload_id" in init_res
    assert "key" in init_res
    assert len(init_res["presigned_urls"]) == 3

    # Test complete multipart mock
    complete_res = client.complete_multipart_upload(
        init_res["upload_id"],
        init_res["key"],
        [{"PartNumber": 1, "ETag": '"etag1"'}],
    )
    assert complete_res["status"] == "success"

    # Test file entry creation mock
    entry_res = client.create_file_entry(
        filename=init_res["key"],
        client_name="my_photo.jpg",
        size=5000,
        client_mime="image/jpeg",
    )
    assert "fileEntry" in entry_res
    assert entry_res["fileEntry"]["hash"] is not None

    # Test folder creation mock
    folder_res = client.create_folder("Project Vault")
    assert "folder" in folder_res
    assert folder_res["folder"]["name"] == "Project Vault"

    # Test download URL resolution
    dl_url = client.get_download_url("sampleHash123")
    assert dl_url == "https://spacebyte.in/api/v1/file-entries/download/sampleHash123"


@pytest.mark.django_db
def test_1tb_storage_pool_capacity_check(subscribed_user):
    # Within 1 TB pool limit
    check_storage_pool_capacity(100 * 1024 * 1024)

    # Exceeding the 1 TB pool limit (over 1000 GB)
    exorbitant_bytes = (1001 * 1024 * 1024 * 1024)
    with pytest.raises(QuotaExceededException):
        check_storage_pool_capacity(exorbitant_bytes)


@pytest.mark.django_db
def test_storage_pool_status_api(subscribed_user):
    api_client = APIClient()
    api_client.force_authenticate(user=subscribed_user)

    # Regular user is forbidden from viewing the upstream testing pool
    response_forbidden = api_client.get("/api/v1/storage/pool-status")
    assert response_forbidden.status_code == 403

    # Master Admin can inspect pool status
    subscribed_user.is_staff = True
    subscribed_user.save(update_fields=["is_staff"])
    response = api_client.get("/api/v1/storage/pool-status")
    assert response.status_code == 200
    data = response.json()
    assert "total_pool_bytes" in data
    assert "committed_bytes" in data
    assert "uncommitted_gb" in data
    assert "committed_percent" in data
    assert data["provider"] == "spacebyte"
    assert "user_quota" in data
    assert "billing_intervals_supported" in data
    assert "monthly" in data["billing_intervals_supported"]
    assert "yearly" in data["billing_intervals_supported"]


@pytest.mark.django_db
def test_no_auth_redirect_handler_strips_auth():
    from apps.storage.spacebyte import NoAuthRedirectHandler
    import urllib.request

    handler = NoAuthRedirectHandler()
    req = urllib.request.Request(
        "https://spacebyte.in/api/v1/file-entries/download/test",
        headers={"Authorization": "Bearer sample_token", "User-Agent": "test"},
    )
    # Simulate redirect to S3 / Cloudflare R2 presigned URL
    new_req = handler.redirect_request(
        req,
        None,
        302,
        "Found",
        {"Location": "https://account.r2.cloudflarestorage.com/bucket/file?X-Amz-Signature=123"},
        "https://account.r2.cloudflarestorage.com/bucket/file?X-Amz-Signature=123",
    )
    assert new_req is not None
    assert "Authorization" not in new_req.headers
    assert "authorization" not in new_req.headers


@pytest.mark.django_db
def test_download_stream_unconfigured():
    from apps.storage.spacebyte import SpaceByteClient, SpaceByteError

    client = SpaceByteClient(access_token="")
    with pytest.raises(SpaceByteError) as exc_info:
        client.download_stream("sampleHash")
    assert exc_info.value.status_code == 401


@pytest.mark.django_db
def test_node_content_view_spacebyte_streaming(subscribed_user):
    import io
    from unittest.mock import patch
    from apps.storage.models import Node, FileVersion

    # Create node with spacebyte_hash
    node = Node.objects.create(
        owner=subscribed_user,
        type=Node.TYPE_FILE,
        encrypted_name="ZW5jcnlwdGVkX25hbWU=",
        name_nonce="1122334455667788",
        size_bytes=100,
        spacebyte_hash="mock_hash_123",
    )
    FileVersion.objects.create(
        node=node,
        version_no=1,
        object_key="mock_key",
        size_bytes=100,
        wrapped_file_key="mock_wrapped",
        content_nonce="mock_nonce",
    )

    api_client = APIClient()
    api_client.force_authenticate(user=subscribed_user)

    # 1. When SpaceByte is not configured
    with patch("apps.storage.views.get_spacebyte_client") as mock_get_client:
        mock_client = mock_get_client.return_value
        mock_client.is_configured = False
        mock_client.download_stream.side_effect = Exception("Not configured")

        res = api_client.get(f"/api/v1/nodes/{node.id}/content")
        assert res.status_code == 502
        assert res.data["code"] == "spacebyte_not_configured"

    # 2. When SpaceByte successfully streams
    with patch("apps.storage.views.get_spacebyte_client") as mock_get_client:
        mock_client = mock_get_client.return_value
        mock_client.is_configured = True
        mock_client.download_stream.return_value = (
            io.BytesIO(b"encrypted file content bytes"),
            200,
            {
                "Content-Length": "28",
                "Content-Range": "",
                "Content-Type": "application/octet-stream",
                "Accept-Ranges": "bytes",
            },
        )

        res = api_client.get(f"/api/v1/nodes/{node.id}/content")
        assert res.status_code == 200
        assert res["Content-Length"] == "28"
        assert res["Accept-Ranges"] == "bytes"
        # Read streaming content
        content = b"".join(res.streaming_content)
        assert content == b"encrypted file content bytes"

