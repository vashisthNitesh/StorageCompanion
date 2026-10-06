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
