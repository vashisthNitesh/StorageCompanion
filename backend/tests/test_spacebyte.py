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

    response = api_client.get("/api/v1/storage/pool-status")
    assert response.status_code == 200
    data = response.json()
    assert "total_pool_bytes" in data
    assert data["provider"] == "spacebyte"
    assert "user_quota" in data
    assert "billing_intervals_supported" in data
    assert "monthly" in data["billing_intervals_supported"]
    assert "yearly" in data["billing_intervals_supported"]
