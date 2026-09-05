import pytest
from apps.accounts.models import User
from apps.storage.models import Node, FileVersion
from apps.sharing.models import Share


@pytest.mark.django_db
def test_public_share_with_password(auth_client, subscribed_user):
    # Create file node
    node = Node.objects.create(
        owner=subscribed_user,
        type=Node.TYPE_FILE,
        encrypted_name="cHJpdmF0ZV9kb2M=",
        name_nonce="nonce123456",
        size_bytes=1024,
    )
    FileVersion.objects.create(
        node=node,
        version_no=1,
        object_key="vault/test/key.enc",
        size_bytes=1024,
        wrapped_file_key="wrapped_file_key_1",
        content_nonce="content_nonce_1",
    )

    # Create link share with password
    payload = {
        "node_id": str(node.id),
        "type": "link",
        "wrapped_key": "wrapped_link_key_abc",
        "permission": "download",
        "password": "SecretPassword123!",
        "max_downloads": 2,
    }
    res = auth_client.post("/api/v1/shares", payload, format="json")
    assert res.status_code == 201
    raw_token = res.data["raw_token"]

    # Public unauthenticated fetch without password
    from rest_framework.test import APIClient
    public_client = APIClient()

    res_pub = public_client.get(f"/api/v1/public/shares/{raw_token}")
    assert res_pub.status_code == 200
    assert res_pub.data["requires_password"] is True
    assert res_pub.data["wrapped_key"] is None  # Hidden until password verified

    # Auth with incorrect password
    res_wrong = public_client.post(f"/api/v1/public/shares/{raw_token}/auth", {"password": "WrongPassword"})
    assert res_wrong.status_code == 403

    # Auth with correct password
    res_correct = public_client.post(f"/api/v1/public/shares/{raw_token}/auth", {"password": "SecretPassword123!"})
    assert res_correct.status_code == 200
    assert res_correct.data["wrapped_key"] == "wrapped_link_key_abc"
