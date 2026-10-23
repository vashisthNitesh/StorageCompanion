import pytest
from apps.accounts.models import User
from apps.storage.models import Node, FileVersion, StorageQuota
from tests.conftest import bearer_client_for, relay_all_parts

PART = 20 * 1024 * 1024
COMPLETE = {"wrapped_file_key": "wrapped_key_test", "content_nonce": "content_nonce_test"}


def init_upload(client, size_bytes, **extra):
    return client.post(
        "/api/v1/uploads",
        {"encrypted_name": "ZW5jcnlwdGVkX2ZpbGU=", "name_nonce": "1122334455667788", "size_bytes": size_bytes, **extra},
        format="json",
    )


@pytest.mark.django_db
def test_quota_enforcement_at_boundaries(auth_client, subscribed_user, sample_plan):
    quota = StorageQuota.objects.get(user=subscribed_user)  # 100 MB

    res = init_upload(auth_client, 20 * 1024 * 1024)
    assert res.status_code == 201
    assert "presigned_urls" not in res.data  # parts always go through the relay
    upload_id = res.data["upload_session_id"]

    relay_all_parts(auth_client, upload_id, 20 * 1024 * 1024, res.data["part_size"])
    res_comp = auth_client.post(f"/api/v1/uploads/{upload_id}/complete", COMPLETE, format="json")
    assert res_comp.status_code == 200, res_comp.content

    quota.refresh_from_db()
    assert quota.bytes_used == 20 * 1024 * 1024

    quota.bytes_used = 90 * 1024 * 1024
    quota.save()
    res_excess = init_upload(auth_client, 20 * 1024 * 1024)
    assert res_excess.status_code == 413
    assert res_excess.data["code"] == "QUOTA_EXCEEDED"


@pytest.mark.django_db
def test_size_is_taken_from_received_parts_not_the_browser(auth_client, subscribed_user):
    res = init_upload(auth_client, 1024)
    upload_id = res.data["upload_session_id"]

    # A part bigger than the declared size is refused
    too_big = auth_client.post(
        f"/api/v1/uploads/{upload_id}/parts/1", data=b"\0" * (5 * 1024 * 1024), content_type="application/octet-stream"
    )
    assert too_big.status_code == 400
    # Part numbers outside the declared range are refused
    extra = auth_client.post(
        f"/api/v1/uploads/{upload_id}/parts/2", data=b"\0" * (1024 + 16), content_type="application/octet-stream"
    )
    assert extra.status_code == 400

    # Completing without the parts is refused
    assert auth_client.post(f"/api/v1/uploads/{upload_id}/complete", COMPLETE, format="json").status_code == 400

    relay_all_parts(auth_client, upload_id, 1024, PART)
    done = auth_client.post(f"/api/v1/uploads/{upload_id}/complete", COMPLETE, format="json")
    assert done.status_code == 200
    assert done.data["size_bytes"] == 1024
    assert StorageQuota.objects.get(user=subscribed_user).bytes_used == 1024


@pytest.mark.django_db
def test_plan_max_file_size_is_enforced(auth_client, sample_plan):
    res = init_upload(auth_client, sample_plan.max_file_size + 1)
    assert res.status_code == 413
    assert res.data["code"] == "FILE_TOO_LARGE"


@pytest.mark.django_db
def test_unsubscribed_user_cannot_upload():
    unsub_user = User.objects.create_user(email="unsubscribed@example.com", password="TestPassword123!")
    res = init_upload(bearer_client_for(unsub_user), 1024 * 1024)
    assert res.status_code == 402


@pytest.mark.django_db
def test_upload_part_relay(auth_client):
    res = init_upload(auth_client, 1024)
    upload_id = res.data["upload_session_id"]
    relay_res = auth_client.post(
        f"/api/v1/uploads/{upload_id}/parts/1", data=b"\1" * (1024 + 16), content_type="application/octet-stream"
    )
    assert relay_res.status_code == 200
    assert relay_res.data["status"] == "success"
    assert relay_res.data["part_number"] == 1


@pytest.mark.django_db
def test_download_info_routes_through_authenticated_stream(auth_client, subscribed_user):
    node = Node.objects.create(
        owner=subscribed_user, type=Node.TYPE_FILE, encrypted_name="ZW5j", name_nonce="123456", size_bytes=100
    )
    FileVersion.objects.create(
        node=node, version_no=1, object_key="mock_key_1", size_bytes=100, wrapped_file_key="key", content_nonce="nonce"
    )

    dl_res = auth_client.get(f"/api/v1/nodes/{node.id}/download")
    assert dl_res.status_code == 200
    assert dl_res.data["download_url"] == f"/api/v1/nodes/{node.id}/content"
    assert dl_res.data["part_size"] == 8 * 1024 * 1024
    assert dl_res.data["size_bytes"] == 100


@pytest.mark.django_db
def test_download_info_purpose_controls_activity_log(auth_client, subscribed_user):
    from apps.audit.models import AuditLog

    node = Node.objects.create(
        owner=subscribed_user, type=Node.TYPE_FILE, encrypted_name="ZW5j", name_nonce="123456", size_bytes=100
    )
    FileVersion.objects.create(
        node=node, version_no=1, object_key="mock_key_1", size_bytes=100, wrapped_file_key="key", content_nonce="nonce"
    )
    actions = lambda: list(AuditLog.objects.filter(target_id=str(node.id)).values_list("action", flat=True))

    assert auth_client.get(f"/api/v1/nodes/{node.id}/download?purpose=thumbnail").status_code == 200
    assert actions() == []
    assert auth_client.get(f"/api/v1/nodes/{node.id}/download?purpose=preview").status_code == 200
    assert actions() == ["file.previewed"]
    assert auth_client.get(f"/api/v1/nodes/{node.id}/download").status_code == 200
    assert sorted(actions()) == ["file.downloaded", "file.previewed"]


@pytest.mark.django_db
def test_other_users_cannot_download(subscribed_user):
    node = Node.objects.create(
        owner=subscribed_user, type=Node.TYPE_FILE, encrypted_name="ZW5j", name_nonce="1", size_bytes=1
    )
    other = User.objects.create_user(email="other@example.com", password="OtherPassword123!")
    client = bearer_client_for(other)
    assert client.get(f"/api/v1/nodes/{node.id}/download").status_code == 404
    assert client.get(f"/api/v1/nodes/{node.id}/content").status_code == 404


@pytest.mark.django_db
def test_folder_cannot_be_moved_into_its_own_subfolder(auth_client, subscribed_user):
    parent = Node.objects.create(owner=subscribed_user, type=Node.TYPE_FOLDER, encrypted_name="cA==", name_nonce="1")
    child = Node.objects.create(
        owner=subscribed_user, type=Node.TYPE_FOLDER, encrypted_name="Yw==", name_nonce="2", parent=parent
    )
    assert auth_client.patch(f"/api/v1/nodes/{parent.id}", {"parent": str(child.id)}, format="json").status_code == 400
    assert auth_client.patch(f"/api/v1/nodes/{parent.id}", {"parent": str(parent.id)}, format="json").status_code == 400
    assert auth_client.patch(f"/api/v1/nodes/{child.id}", {"parent": None}, format="json").status_code == 200


@pytest.mark.django_db
def test_listing_is_not_truncated_and_trash_shows_top_level_only(auth_client, subscribed_user):
    folder = Node.objects.create(owner=subscribed_user, type=Node.TYPE_FOLDER, encrypted_name="Zg==", name_nonce="1")
    for i in range(60):
        Node.objects.create(
            owner=subscribed_user, type=Node.TYPE_FILE, encrypted_name="ZQ==", name_nonce=str(i), parent=folder
        )
    res = auth_client.get(f"/api/v1/nodes?parent={folder.id}")
    assert len(res.data) == 60

    assert auth_client.delete(f"/api/v1/nodes/{folder.id}").status_code == 200
    trashed = auth_client.get("/api/v1/nodes?trashed=true").data
    assert [n["id"] for n in trashed] == [str(folder.id)]


@pytest.mark.django_db
def test_quota_runtime_updates_on_trash_restore_and_delete(auth_client, subscribed_user):
    from apps.storage.services import recalculate_user_quota

    file_size = 5 * 1024 * 1024
    node = Node.objects.create(
        owner=subscribed_user,
        type=Node.TYPE_FILE,
        encrypted_name="dGVzdF9maWxl",
        name_nonce="1234567890",
        size_bytes=file_size,
    )
    FileVersion.objects.create(
        node=node,
        version_no=1,
        object_key="obj_key_1",
        size_bytes=file_size,
        wrapped_file_key="wrapped_key",
        content_nonce="nonce",
    )

    quota = recalculate_user_quota(subscribed_user)
    assert quota.bytes_used == file_size

    del_res = auth_client.delete(f"/api/v1/nodes/{node.id}")
    assert del_res.status_code == 200
    assert del_res.data["quota"]["bytes_used"] == 0

    restore_res = auth_client.post(f"/api/v1/nodes/{node.id}/restore")
    assert restore_res.status_code == 200
    assert restore_res.data["quota"]["bytes_used"] == file_size

    perm_del_res = auth_client.delete(f"/api/v1/nodes/{node.id}?permanent=true")
    assert perm_del_res.status_code == 200
    assert perm_del_res.data["quota"]["bytes_used"] == 0


@pytest.mark.django_db
def test_new_version_keeps_name_and_adds_version(auth_client, subscribed_user):
    first = init_upload(auth_client, 100)
    relay_all_parts(auth_client, first.data["upload_session_id"], 100, PART)
    node = auth_client.post(f"/api/v1/uploads/{first.data['upload_session_id']}/complete", COMPLETE, format="json").data

    second = init_upload(auth_client, 300, node_id=node["id"], encrypted_name="b3RoZXJfbmFtZQ==")
    assert second.status_code == 201
    relay_all_parts(auth_client, second.data["upload_session_id"], 300, PART)
    done = auth_client.post(f"/api/v1/uploads/{second.data['upload_session_id']}/complete", COMPLETE, format="json")
    assert done.status_code == 200
    assert done.data["id"] == node["id"]
    assert done.data["encrypted_name"] == node["encrypted_name"]
    assert done.data["size_bytes"] == 300
    versions = auth_client.get(f"/api/v1/nodes/{node['id']}/versions").data
    assert [v["version_no"] for v in versions] == [2, 1]
