"""Streaming part relay: bytes go to storage as they arrive, with fresh presigned URLs."""
import http.server
import threading

import pytest

from apps.storage import services
from apps.storage.models import Upload

PART = 1024


class FakeStorage:
    """A local stand-in for presigned PUT URLs that records what it receives."""

    def __init__(self):
        self.received = []  # (path, headers, body)
        self.reject_next = 0
        storage = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_PUT(self):
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                storage.received.append((self.path, dict(self.headers), body))
                if storage.reject_next:
                    storage.reject_next -= 1
                    self.send_response(403)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("ETag", f'"etag-{len(storage.received)}"')
                self.send_header("Content-Length", "0")
                self.end_headers()

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()


@pytest.fixture
def storage(monkeypatch):
    fake = FakeStorage()
    signed = []

    class Client:
        def sign_part_urls(self, upload_id, key, numbers):
            signed.append(list(numbers))
            return {n: f"{fake.base}/{key}?part={n}&sig={len(signed)}" for n in numbers}

    monkeypatch.setattr(services, "get_spacebyte_client", lambda: Client())
    services._part_urls.clear()
    fake.signed = signed
    yield fake
    fake.close()


def make_upload(user, size, part_size=PART):
    return Upload.objects.create(
        user=user,
        upload_id="u1",
        object_key=f"uploads/k-{size}.bin",
        spacebyte_upload_id="sb1",
        spacebyte_key="uploads/k.bin",
        encrypted_name="ZW5j",
        name_nonce="00",
        expected_size_bytes=size,
        part_size=part_size,
        status=Upload.STATUS_UPLOADING,
        expires_at="2099-01-01T00:00:00Z",
    )


def post_part(client, upload, n, body):
    return client.post(f"/api/v1/uploads/{upload.id}/parts/{n}", data=body, content_type="application/octet-stream")


@pytest.mark.django_db
def test_part_is_streamed_with_exact_length_and_etag_recorded(auth_client, subscribed_user, storage):
    upload = make_upload(subscribed_user, size=PART * 2 + 100)
    body = bytes(range(256)) * 4 + b"\x01" * 16  # 1040 bytes
    res = post_part(auth_client, upload, 1, body)
    assert res.status_code == 200, res.content
    path, headers, received = storage.received[-1]
    assert received == body
    assert headers.get("Content-Length") == str(len(body))
    assert "Transfer-Encoding" not in headers
    upload.refresh_from_db()
    assert upload.received_parts["1"] == {"etag": '"etag-1"', "size": len(body)}
    # URLs are signed just in time, in one small batch covering the following parts too.
    assert storage.signed == [[1, 2, 3]]


@pytest.mark.django_db
def test_rejected_url_is_resigned_on_the_next_attempt(auth_client, subscribed_user, storage):
    upload = make_upload(subscribed_user, size=PART * 3)
    body = b"\0" * (PART + 16)
    storage.reject_next = 1
    first = post_part(auth_client, upload, 2, body)
    assert first.status_code == 502
    second = post_part(auth_client, upload, 2, body)
    assert second.status_code == 200, second.content
    # The failed URL was dropped, so the retry used a freshly signed one.
    assert len(storage.signed) == 2
    assert storage.received[0][0] != storage.received[1][0]


@pytest.mark.django_db
def test_wrong_length_is_refused_before_contacting_storage(auth_client, subscribed_user, storage):
    upload = make_upload(subscribed_user, size=PART * 2)
    res = post_part(auth_client, upload, 1, b"\0" * 10)
    assert res.status_code == 400
    assert storage.received == []


@pytest.mark.django_db
def test_inactive_session_reports_conflict(auth_client, subscribed_user, storage):
    upload = make_upload(subscribed_user, size=PART)
    upload.status = Upload.STATUS_ABORTED
    upload.save()
    res = post_part(auth_client, upload, 1, b"\0" * (PART + 16))
    assert res.status_code == 409
    assert res.data["code"] == "upload_inactive"


@pytest.mark.django_db
def test_init_signs_only_the_first_batch(subscribed_user, settings, monkeypatch):
    calls = {}

    class Client:
        def init_multipart_upload(self, **kwargs):
            calls.update(kwargs)
            return {"upload_id": "sb", "key": "uploads/x.bin", "presigned_urls": []}

    monkeypatch.setattr(services, "get_spacebyte_client", lambda: Client())
    monkeypatch.setattr(services, "check_quota_available", lambda *a: None)
    services.init_multipart_upload(subscribed_user, encrypted_name="ZW5j", name_nonce="00", size_bytes=40 * 1024**3)
    assert calls["part_count"] == 5120  # 40 GiB in 8 MiB parts
    assert calls["sign_count"] == services.PART_SIGN_BATCH
