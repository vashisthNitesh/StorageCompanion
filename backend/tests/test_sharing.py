import pytest

from apps.storage.models import FileVersion, Node


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


def _make_password_share(auth_client, owner, password="SecretPassword123!"):
    node = Node.objects.create(owner=owner, type=Node.TYPE_FILE, encrypted_name="ZQ==", name_nonce="n", size_bytes=10)
    FileVersion.objects.create(node=node, version_no=1, object_key="vault/k", size_bytes=10,
                               wrapped_file_key="w", content_nonce="00")
    res = auth_client.post("/api/v1/shares", {"node_id": str(node.id), "type": "link", "wrapped_key": "wk",
                                              "permission": "download", "password": password}, format="json")
    assert res.status_code == 201
    return node, res.data["raw_token"]


@pytest.mark.django_db
def test_public_download_with_password_does_not_crash(auth_client, subscribed_user):
    from rest_framework.test import APIClient

    _, token = _make_password_share(auth_client, subscribed_user)
    res = APIClient().get(f"/api/v1/public/shares/{token}/download", {"password": "SecretPassword123!"})
    # used to be a 500 (NameError: urllib not imported)
    assert res.status_code == 200
    assert "password=" in res.data["download_url"]


@pytest.mark.django_db
def test_share_of_trashed_file_stops_working(auth_client, subscribed_user):
    from rest_framework.test import APIClient

    node, token = _make_password_share(auth_client, subscribed_user)
    assert auth_client.delete(f"/api/v1/nodes/{node.id}").status_code == 200
    res = APIClient().get(f"/api/v1/public/shares/{token}")
    assert res.status_code == 404


@pytest.mark.django_db
def test_share_password_guessing_is_throttled(auth_client, subscribed_user):
    from rest_framework.test import APIClient

    _, token = _make_password_share(auth_client, subscribed_user)
    c = APIClient()
    codes = [c.post(f"/api/v1/public/shares/{token}/auth", {"password": f"guess{i}"}).status_code for i in range(25)]
    assert codes[0] == 403
    assert 429 in codes
    # Viewing the link without a password is not counted against the guess limit
    assert c.get(f"/api/v1/public/shares/{token}").status_code == 200
