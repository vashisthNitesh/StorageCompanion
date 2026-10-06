from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.billing.models import Subscription
from apps.storage.models import FileVersion, Node, StorageQuota


@pytest.fixture
def other_client(db, sample_plan):
    user = User.objects.create_user(email="mallory@test.local", password="MalloryPass123!")
    Subscription.objects.create(
        user=user, plan=sample_plan, status="active",
        current_period_start=timezone.now(), current_period_end=timezone.now() + timedelta(days=30),
    )
    StorageQuota.objects.create(user=user, bytes_limit=sample_plan.storage_bytes)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def make_file(owner):
    node = Node.objects.create(owner=owner, type=Node.TYPE_FILE, encrypted_name="ZQ==", name_nonce="n", size_bytes=10)
    FileVersion.objects.create(node=node, version_no=1, object_key=f"k/{node.id}", size_bytes=10,
                               wrapped_file_key="owner_key", content_nonce="00")
    return node


@pytest.mark.django_db
def test_cannot_overwrite_other_users_file_via_upload_node_id(other_client, subscribed_user):
    victim = make_file(subscribed_user)
    res = other_client.post("/api/v1/uploads", {"encrypted_name": "aA==", "name_nonce": "n", "size_bytes": 5,
                                                "node_id": str(victim.id)}, format="json")
    assert res.status_code == 404
    assert FileVersion.objects.filter(node=victim).count() == 1


@pytest.mark.django_db
def test_owner_can_upload_new_version(auth_client, subscribed_user):
    node = make_file(subscribed_user)
    res = auth_client.post("/api/v1/uploads", {"encrypted_name": "aA==", "name_nonce": "n", "size_bytes": 5,
                                               "node_id": str(node.id)}, format="json")
    assert res.status_code == 201
    res = auth_client.post(f"/api/v1/uploads/{res.data['upload_session_id']}/complete",
                           {"parts": [{"part_number": 1}], "wrapped_file_key": "v2", "content_nonce": "00"},
                           format="json")
    assert res.status_code == 200
    assert FileVersion.objects.filter(node=node).count() == 2


@pytest.mark.django_db
def test_folder_move_cycles_rejected(auth_client):
    a = auth_client.post("/api/v1/nodes", {"encrypted_name": "YQ==", "name_nonce": "n"}, format="json").data
    b = auth_client.post("/api/v1/nodes", {"encrypted_name": "Yg==", "name_nonce": "n", "parent": a["id"]},
                         format="json").data
    assert auth_client.patch(f"/api/v1/nodes/{a['id']}", {"parent": a["id"]}, format="json").status_code == 400
    assert auth_client.patch(f"/api/v1/nodes/{a['id']}", {"parent": b["id"]}, format="json").status_code == 400
    # legit move back to root still works
    assert auth_client.patch(f"/api/v1/nodes/{b['id']}", {"parent": None}, format="json").status_code == 200


@pytest.mark.django_db
def test_bad_query_params_return_400(auth_client, subscribed_user):
    node = make_file(subscribed_user)
    assert auth_client.get("/api/v1/nodes?parent=not-a-uuid").status_code == 400
    assert auth_client.get(f"/api/v1/nodes/{node.id}/download?v=abc").status_code == 400
    assert auth_client.get(f"/api/v1/nodes/{node.id}/content?v=abc").status_code == 400


@pytest.mark.django_db
def test_plan_max_file_size_enforced(auth_client, sample_plan):
    sample_plan.storage_bytes = 10 * 1024**3
    sample_plan.save()
    StorageQuota.objects.update(bytes_limit=10 * 1024**3)
    res = auth_client.post("/api/v1/uploads", {"encrypted_name": "aA==", "name_nonce": "n",
                                               "size_bytes": sample_plan.max_file_size + 1}, format="json")
    assert res.status_code == 413
    assert res.data["code"] == "FILE_TOO_LARGE"


@pytest.mark.django_db
def test_complete_requires_part_numbers(auth_client):
    res = auth_client.post("/api/v1/uploads", {"encrypted_name": "aA==", "name_nonce": "n", "size_bytes": 5},
                           format="json")
    res = auth_client.post(f"/api/v1/uploads/{res.data['upload_session_id']}/complete",
                           {"parts": [{"etag": "x"}], "wrapped_file_key": "k", "content_nonce": "00"}, format="json")
    assert res.status_code == 400


@pytest.mark.django_db
def test_complete_does_not_create_file_when_storage_finalize_fails(auth_client, subscribed_user, monkeypatch, fake_s3):
    api_client, user = auth_client, subscribed_user
    monkeypatch.setattr(fake_s3, "create_multipart_upload", lambda **kw: {"UploadId": "real-upload-1"})

    def boom(**kw):
        raise RuntimeError("InvalidPart")

    monkeypatch.setattr(fake_s3, "complete_multipart_upload", boom)
    init = api_client.post("/api/v1/uploads", {"encrypted_name": "bmFtZQ==", "name_nonce": "abc", "size_bytes": 10}, format="json")
    assert init.status_code == 201
    res = api_client.post(
        f"/api/v1/uploads/{init.data['upload_session_id']}/complete",
        {"parts": [{"part_number": 1, "etag": '"1"'}], "wrapped_file_key": "k", "content_nonce": "n"},
        format="json",
    )
    assert res.status_code == 502
    assert not Node.objects.filter(owner=user, type=Node.TYPE_FILE).exists()


@pytest.mark.django_db
def test_complete_uses_server_side_etags(auth_client, monkeypatch, fake_s3):
    api_client = auth_client
    monkeypatch.setattr(fake_s3, "create_multipart_upload", lambda **kw: {"UploadId": "real-upload-2"})
    monkeypatch.setattr(fake_s3, "list_parts", lambda **kw: {"Parts": [{"PartNumber": 1, "ETag": '"abc123"'}]})
    seen = {}
    monkeypatch.setattr(fake_s3, "complete_multipart_upload", lambda **kw: seen.update(kw) or {})
    init = api_client.post("/api/v1/uploads", {"encrypted_name": "bmFtZQ==", "name_nonce": "abc", "size_bytes": 10}, format="json")
    res = api_client.post(
        f"/api/v1/uploads/{init.data['upload_session_id']}/complete",
        {"parts": [{"part_number": 1}], "wrapped_file_key": "k", "content_nonce": "n"},
        format="json",
    )
    assert res.status_code == 200, res.data
    assert seen["MultipartUpload"]["Parts"] == [{"PartNumber": 1, "ETag": '"abc123"'}]


@pytest.mark.django_db
def test_trash_list_and_restore_out_of_trashed_folder(auth_client, subscribed_user):
    folder = Node.objects.create(owner=subscribed_user, type=Node.TYPE_FOLDER, encrypted_name="Zg==", name_nonce="n")
    child = make_file(subscribed_user)
    child.parent = folder
    child.save()
    assert auth_client.delete(f"/api/v1/nodes/{child.id}").status_code == 200
    assert auth_client.delete(f"/api/v1/nodes/{folder.id}").status_code == 200
    listed = auth_client.get("/api/v1/nodes?trashed=true").data
    ids = {n["id"] for n in (listed["results"] if isinstance(listed, dict) else listed)}
    assert {str(folder.id), str(child.id)} <= ids
    assert auth_client.post(f"/api/v1/nodes/{child.id}/restore").status_code == 200
    child.refresh_from_db()
    assert child.trashed_at is None and child.parent_id is None  # moved to root, visible again


@pytest.mark.django_db
def test_cannot_restore_other_users_node(other_client, subscribed_user):
    node = make_file(subscribed_user)
    assert other_client.post(f"/api/v1/nodes/{node.id}/restore").status_code == 404
