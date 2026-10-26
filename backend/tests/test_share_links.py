"""Public file links: ownership, expiry, revocation, download limits and passwords."""
import hashlib
from datetime import timedelta
from unittest import mock

import pytest
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.links.models import ShareLink
from apps.storage.models import FileVersion, Node
from tests.conftest import bearer_client_for

PROOF = "5a" * 32
PROOF_HASH = hashlib.sha256(bytes.fromhex(PROOF)).hexdigest()


@pytest.fixture
def file_node(subscribed_user):
    node = Node.objects.create(
        owner=subscribed_user, type=Node.TYPE_FILE, encrypted_name="enc", name_nonce="nn", size_bytes=1234, spacebyte_hash="hash1"
    )
    FileVersion.objects.create(node=node, version_no=1, object_key="obj-1", size_bytes=1234, part_size=8 * 1024 * 1024,
                               wrapped_file_key="wfk", content_nonce="cn")
    return node


def share_body(**extra):
    return {
        "expires_in": "7d",
        "wrapped_key": "share-wrapped-file-key",
        "encrypted_name": "share-enc-name",
        "name_nonce": "share-nonce",
        "owner_wrapped_link_key": "owner-wrapped",
        **extra,
    }


def create(client, node, **extra):
    res = client.post(f"/api/v1/nodes/{node.id}/shares", share_body(**extra), format="json")
    assert res.status_code == 201, res.content
    return res.data


def fake_stream():
    return mock.patch("apps.links.views.stream_node_content", return_value=HttpResponse(b"ciphertext", content_type="application/octet-stream"))


# -- Owner side ---------------------------------------------------------------

@pytest.mark.django_db
def test_only_the_owner_can_create_list_and_revoke(auth_client, file_node):
    link = create(auth_client, file_node)
    assert link["status"] == "active" and len(link["token"]) >= 20

    stranger = User.objects.create_user(email="stranger@example.com", password="StrangerPass123!")
    other = bearer_client_for(stranger)
    assert other.post(f"/api/v1/nodes/{file_node.id}/shares", share_body(), format="json").status_code == 404
    assert other.get(f"/api/v1/nodes/{file_node.id}/shares").status_code == 404
    assert other.delete(f"/api/v1/shares/{link['id']}").status_code == 404
    assert ShareLink.objects.get(id=link["id"]).revoked_at is None
    assert APIClient().post(f"/api/v1/nodes/{file_node.id}/shares", share_body(), format="json").status_code == 401

    listed = auth_client.get(f"/api/v1/nodes/{file_node.id}/shares").data
    assert [x["id"] for x in listed] == [link["id"]]
    assert "wrapped_key" not in listed[0]


@pytest.mark.django_db
def test_folders_and_trashed_files_cannot_be_shared(auth_client, subscribed_user, file_node):
    folder = Node.objects.create(owner=subscribed_user, type=Node.TYPE_FOLDER, encrypted_name="f", name_nonce="n")
    assert auth_client.post(f"/api/v1/nodes/{folder.id}/shares", share_body(), format="json").status_code == 400
    file_node.trashed_at = timezone.now()
    file_node.save()
    assert auth_client.post(f"/api/v1/nodes/{file_node.id}/shares", share_body(), format="json").status_code == 400


@pytest.mark.django_db
def test_expiry_choices(auth_client, file_node):
    before = timezone.now()
    hour = create(auth_client, file_node, expires_in="1h")
    never = create(auth_client, file_node, expires_in="never")
    assert ShareLink.objects.get(id=never["id"]).expires_at is None
    expires = ShareLink.objects.get(id=hour["id"]).expires_at
    assert timedelta(minutes=59) < expires - before <= timedelta(hours=1, seconds=5)
    assert auth_client.post(f"/api/v1/nodes/{file_node.id}/shares", share_body(expires_in="2y"), format="json").status_code == 400


# -- Public side -----------------------------------------------------------------

@pytest.mark.django_db
def test_public_page_gets_the_wrapped_key_without_counting(auth_client, file_node):
    link = create(auth_client, file_node, max_downloads=1)
    public = APIClient()
    info = public.get(f"/api/v1/s/{link['token']}")
    assert info.status_code == 200
    assert info.data["wrapped_key"] == "share-wrapped-file-key" and info.data["size_bytes"] == 1234
    assert info["Cache-Control"] == "no-store"
    public.get(f"/api/v1/s/{link['token']}")
    assert ShareLink.objects.get(id=link["id"]).download_count == 0


@pytest.mark.django_db
def test_download_limit_is_enforced(auth_client, file_node):
    link = create(auth_client, file_node, max_downloads=2)
    public = APIClient()
    for _ in range(2):
        assert public.post(f"/api/v1/s/{link['token']}/open", {}, format="json").status_code == 200
    third = public.post(f"/api/v1/s/{link['token']}/open", {}, format="json")
    assert third.status_code == 410 and third.data["code"] == "SHARE_LIMIT_REACHED"
    assert ShareLink.objects.get(id=link["id"]).download_count == 2
    assert public.get(f"/api/v1/s/{link['token']}").data["code"] == "SHARE_LIMIT_REACHED"


@pytest.mark.django_db
def test_expired_links_refuse_everything(auth_client, file_node):
    link = create(auth_client, file_node)
    public = APIClient()
    grant = public.post(f"/api/v1/s/{link['token']}/open", {}, format="json").data["grant"]
    ShareLink.objects.filter(id=link["id"]).update(expires_at=timezone.now() - timedelta(seconds=1))
    assert public.get(f"/api/v1/s/{link['token']}").data["code"] == "SHARE_EXPIRED"
    assert public.post(f"/api/v1/s/{link['token']}/open", {}, format="json").status_code == 410
    with fake_stream():
        res = public.get(f"/api/v1/s/{link['token']}/content", HTTP_X_SHARE_GRANT=grant)
    assert res.status_code == 410


@pytest.mark.django_db
def test_revoking_stops_new_and_open_downloads(auth_client, file_node):
    link = create(auth_client, file_node)
    public = APIClient()
    grant = public.post(f"/api/v1/s/{link['token']}/open", {}, format="json").data["grant"]
    with fake_stream():
        assert public.get(f"/api/v1/s/{link['token']}/content", HTTP_X_SHARE_GRANT=grant).status_code == 200
    assert auth_client.delete(f"/api/v1/shares/{link['id']}").status_code == 200
    assert public.get(f"/api/v1/s/{link['token']}").data["code"] == "SHARE_REVOKED"
    with fake_stream():
        res = public.get(f"/api/v1/s/{link['token']}/content", HTTP_X_SHARE_GRANT=grant)
    assert res.status_code == 410 and res.data["code"] == "SHARE_REVOKED"
    assert auth_client.get(f"/api/v1/nodes/{file_node.id}/shares").data == []


@pytest.mark.django_db
def test_content_needs_a_grant_for_that_link(auth_client, file_node):
    a = create(auth_client, file_node)
    b = create(auth_client, file_node)
    public = APIClient()
    grant_a = public.post(f"/api/v1/s/{a['token']}/open", {}, format="json").data["grant"]
    with fake_stream():
        assert public.get(f"/api/v1/s/{a['token']}/content").status_code == 410
        assert public.get(f"/api/v1/s/{a['token']}/content", HTTP_X_SHARE_GRANT="forged").status_code == 410
        assert public.get(f"/api/v1/s/{b['token']}/content", HTTP_X_SHARE_GRANT=grant_a).status_code == 404


@pytest.mark.django_db
def test_password_links_hide_the_key_until_the_proof_matches(auth_client, file_node):
    password = {"salt": "ab" * 16, "kdf_params": {"iterations": 3}, "auth_hash": PROOF_HASH}
    link = create(auth_client, file_node, password=password)
    public = APIClient()
    info = public.get(f"/api/v1/s/{link['token']}").data
    assert info["password_protected"] is True and info["password_salt"] == "ab" * 16
    assert "wrapped_key" not in info and "encrypted_name" not in info

    wrong = public.post(f"/api/v1/s/{link['token']}/open", {"password_proof": "00" * 32}, format="json")
    assert wrong.status_code == 403 and wrong.data["code"] == "SHARE_WRONG_PASSWORD"
    assert ShareLink.objects.get(id=link["id"]).download_count == 0

    ok = public.post(f"/api/v1/s/{link['token']}/open", {"password_proof": PROOF}, format="json")
    assert ok.status_code == 200 and ok.data["wrapped_key"] == "share-wrapped-file-key"


@pytest.mark.django_db
def test_wrong_passwords_are_limited_per_link(auth_client, file_node):
    link = create(auth_client, file_node, password={"salt": "ab" * 16, "kdf_params": {}, "auth_hash": PROOF_HASH})
    public = APIClient()
    for _ in range(10):
        public.post(f"/api/v1/s/{link['token']}/open", {"password_proof": "00" * 32}, format="json")
    locked = public.post(f"/api/v1/s/{link['token']}/open", {"password_proof": PROOF}, format="json")
    assert locked.status_code == 429


@pytest.mark.django_db
def test_links_stop_when_the_file_changes_or_is_trashed(auth_client, file_node):
    link = create(auth_client, file_node)
    public = APIClient()
    FileVersion.objects.create(node=file_node, version_no=2, object_key="obj-2", size_bytes=99, wrapped_file_key="w2", content_nonce="c2")
    assert public.get(f"/api/v1/s/{link['token']}").data["code"] == "SHARE_UNAVAILABLE"

    fresh = create(auth_client, file_node)
    file_node.trashed_at = timezone.now()
    file_node.save()
    assert public.post(f"/api/v1/s/{fresh['token']}/open", {}, format="json").data["code"] == "SHARE_UNAVAILABLE"


@pytest.mark.django_db
def test_unknown_tokens_get_a_clear_error():
    res = APIClient().get("/api/v1/s/not-a-real-token")
    assert res.status_code == 404 and res.data["code"] == "SHARE_NOT_FOUND"
