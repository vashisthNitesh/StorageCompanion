import pytest
from apps.accounts.models import User
from apps.storage.models import Node, FileVersion, StorageQuota


@pytest.mark.django_db
def test_quota_enforcement_at_boundaries(auth_client, subscribed_user, sample_plan):
    quota = StorageQuota.objects.get(user=subscribed_user)
    # Quota is 100 MB = 104,857,600 bytes
    
    # 1. Allowed upload: 20 MB
    init_payload = {
        "encrypted_name": "ZW5jcnlwdGVkX2ZpbGU=",
        "name_nonce": "1122334455667788",
        "size_bytes": 20 * 1024 * 1024,
    }
    res = auth_client.post("/api/v1/uploads", init_payload, format="json")
    assert res.status_code == 201
    upload_id = res.data["upload_session_id"]

    # Complete upload
    comp_payload = {
        "parts": [{"part_number": 1, "etag": '"test-etag"'}],
        "wrapped_file_key": "wrapped_key_test",
        "content_nonce": "content_nonce_test",
    }
    res_comp = auth_client.post(f"/api/v1/uploads/{upload_id}/complete", comp_payload, format="json")
    assert res_comp.status_code == 200

    quota.refresh_from_db()
    assert quota.bytes_used == 20 * 1024 * 1024

    # 2. Upload that would exceed remaining quota (remaining is 80 MB, trying 85 MB)
    excess_payload = {
        "encrypted_name": "b3ZlcnNpemVfZmlsZQ==",
        "name_nonce": "1122334455667788",
        "size_bytes": 85 * 1024 * 1024,
    }
    res_excess = auth_client.post("/api/v1/uploads", excess_payload, format="json")
    assert res_excess.status_code == 413
    assert res_excess.data["code"] == "QUOTA_EXCEEDED"


@pytest.mark.django_db
def test_unsubscribed_user_cannot_upload(api_client):
    unsub_user = User.objects.create_user(
        email="unsubscribed@speedcloud.local",
        password="TestPassword123!",
    )
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(unsub_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    payload = {
        "encrypted_name": "ZmlsZQ==",
        "name_nonce": "1122334455667788",
        "size_bytes": 1024 * 1024,
    }
    res = api_client.post("/api/v1/uploads", payload, format="json")
    assert res.status_code == 402  # Payment Required / Subscription Required


@pytest.mark.django_db
def test_upload_part_relay(auth_client, subscribed_user):
    init_payload = {
        "encrypted_name": "ZW5jcnlwdGVkX2ZpbGU=",
        "name_nonce": "1122334455667788",
        "size_bytes": 1024,
    }
    res = auth_client.post("/api/v1/uploads", init_payload, format="json")
    assert res.status_code == 201
    upload_id = res.data["upload_session_id"]

    # Relay chunk upload
    chunk_bytes = b"encrypted chunk bytes"
    relay_res = auth_client.post(
        f"/api/v1/uploads/{upload_id}/parts/1",
        data=chunk_bytes,
        content_type="application/octet-stream",
    )
    assert relay_res.status_code == 200
    assert relay_res.data["status"] == "success"
    assert relay_res.data["part_number"] == 1
    assert "etag" in relay_res.data
