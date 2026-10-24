"""Guards that keep the service usable when many people use it at once."""
import threading
import time

import pytest
from django.contrib.auth.hashers import (
    Argon2PasswordHasher,
    check_password,
    get_hasher,
    make_password,
)
from django.core.cache import cache
from django.test import RequestFactory
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.common.net import get_client_ip
from apps.storage import transfers

PASSWORD = "Shared-Network-Pass-9"


# --- Password hashing ---------------------------------------------------------------------

PRODUCTION_HASHERS = ["apps.accounts.hashers.BoundedArgon2PasswordHasher", "django.contrib.auth.hashers.PBKDF2PasswordHasher"]


@pytest.fixture
def production_hashers(settings):
    settings.PASSWORD_HASHERS = PRODUCTION_HASHERS  # test settings use fast MD5


def test_new_hashes_use_bounded_argon2_parameters(production_hashers):
    encoded = make_password(PASSWORD)
    assert encoded.startswith("argon2$argon2id$")
    assert "m=19456,t=2,p=1" in encoded
    assert check_password(PASSWORD, encoded)


def test_existing_django_default_hashes_still_verify_and_get_upgraded(production_hashers):
    legacy = Argon2PasswordHasher().encode(PASSWORD, Argon2PasswordHasher().salt())
    assert "m=102400" in legacy
    assert check_password(PASSWORD, legacy)
    assert get_hasher("argon2").must_update(legacy)


def test_simultaneous_password_checks_stay_within_the_memory_budget(monkeypatch):
    from apps.accounts import hashers

    running = {"kib": 0, "max_kib": 0, "max_count": 0, "count": 0}
    lock = threading.Lock()

    def slow_verify(self, password, encoded):
        cost = int(hashers._MEMORY_PARAM.search(encoded).group(1))
        with lock:
            running["kib"] += cost
            running["count"] += 1
            running["max_kib"] = max(running["max_kib"], running["kib"])
            running["max_count"] = max(running["max_count"], running["count"])
        time.sleep(0.05)
        with lock:
            running["kib"] -= cost
            running["count"] -= 1
        return True

    monkeypatch.setattr(hashers, "_budget", hashers._MemoryBudget(128 * 1024))
    monkeypatch.setattr(Argon2PasswordHasher, "verify", slow_verify)
    hasher = hashers.BoundedArgon2PasswordHasher()
    new_style = "argon2$argon2id$v=19$m=19456,t=2,p=1$salt$hash"
    old_style = "argon2$argon2id$v=19$m=102400,t=2,p=8$salt$hash"
    threads = [threading.Thread(target=hasher.verify, args=("x", h)) for h in [new_style] * 12 + [old_style] * 4]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert running["max_kib"] <= 128 * 1024
    assert running["max_count"] >= 2  # still runs several at once when they fit


# --- Client IP ------------------------------------------------------------------------------


def test_client_ip_prefers_cloudflare_header_over_forgeable_forwarded_for(settings):
    settings.CLIENT_IP_HEADER = "HTTP_CF_CONNECTING_IP"
    request = RequestFactory().get("/", HTTP_CF_CONNECTING_IP="203.0.113.7", HTTP_X_FORWARDED_FOR="1.2.3.4, 10.0.0.1")
    assert get_client_ip(request) == "203.0.113.7"


def test_client_ip_falls_back_to_forwarded_for_then_remote_addr(settings):
    settings.CLIENT_IP_HEADER = "HTTP_CF_CONNECTING_IP"
    assert get_client_ip(RequestFactory().get("/", HTTP_X_FORWARDED_FOR="198.51.100.2, 10.0.0.1")) == "198.51.100.2"
    assert get_client_ip(RequestFactory().get("/", REMOTE_ADDR="192.0.2.9")) == "192.0.2.9"


# --- Sign-in and refresh limits ---------------------------------------------------------------


@pytest.fixture
def many_accounts(db):
    encoded = make_password(PASSWORD)
    return User.objects.bulk_create(
        [User(email=f"person{i}@college.example", password=encoded, is_active=True) for i in range(15)]
    )


def login(client, email, ip):
    return client.post("/api/v1/auth/login", {"email": email, "password": PASSWORD}, format="json", HTTP_CF_CONNECTING_IP=ip)


@pytest.mark.django_db
def test_people_behind_one_shared_ip_can_all_sign_in(many_accounts):
    cache.clear()
    client = APIClient()
    statuses = [login(client, u.email, "100.64.0.1").status_code for u in many_accounts]
    # 15 different people from one carrier-NAT address: none is rate limited.
    assert statuses.count(200) == 15


@pytest.mark.django_db
def test_one_account_is_limited_whichever_ip_it_comes_from(many_accounts):
    cache.clear()
    client = APIClient()
    email = many_accounts[0].email
    statuses = [login(client, email, f"198.51.100.{i}").status_code for i in range(12)]
    assert statuses[:10] == [200] * 10
    assert statuses[10:] == [429, 429]


@pytest.mark.django_db
def test_refresh_is_limited_per_device_not_per_ip(settings):
    from apps.common.throttles import RefreshSessionThrottle

    def key(sid):
        import base64
        import json

        payload = base64.urlsafe_b64encode(json.dumps({"sid": sid}).encode()).decode().rstrip("=")
        request = RequestFactory().post("/api/v1/auth/refresh", HTTP_CF_CONNECTING_IP="100.64.0.1")
        request.COOKIES[settings.SIMPLE_JWT["AUTH_COOKIE"]] = f"h.{payload}.s"
        return RefreshSessionThrottle().get_cache_key(request, None)

    assert key("device-a") != key("device-b")  # same IP, separate buckets
    assert key("device-a") == key("device-a")


# --- Transfer slots ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_transfers_beyond_the_cap_get_503_and_slots_are_freed(auth_client, subscribed_user, monkeypatch):
    from apps.storage.models import FileVersion, Node

    monkeypatch.setitem(transfers._slots, transfers.DOWNLOAD, threading.BoundedSemaphore(1))
    node = Node.objects.create(owner=subscribed_user, type=Node.TYPE_FILE, encrypted_name="ZW5j", name_nonce="00", size_bytes=4, spacebyte_hash="abc")
    FileVersion.objects.create(node=node, version_no=1, object_key="k1", size_bytes=4, wrapped_file_key="w", content_nonce="n")

    class Upstream:
        def __init__(self):
            self.chunks = [b"data"]
            self.closed = False

        def read(self, n):
            return self.chunks.pop(0) if self.chunks else b""

        def close(self):
            self.closed = True

    upstream = Upstream()

    class Client:
        is_configured = True

        def download_stream(self, *a, **k):
            return upstream, 200, {"Content-Length": "4"}

    monkeypatch.setattr("apps.storage.views.get_spacebyte_client", lambda: Client())

    first = auth_client.get(f"/api/v1/nodes/{node.id}/content")  # holds the only slot until closed
    busy = auth_client.get(f"/api/v1/nodes/{node.id}/content")
    assert busy.status_code == 503
    assert busy["Retry-After"] == str(transfers.RETRY_AFTER_SECONDS)

    assert b"".join(first.streaming_content) == b"data"
    first.close()
    assert upstream.closed
    assert transfers.acquire(transfers.DOWNLOAD)  # slot was returned
    transfers.release(transfers.DOWNLOAD)


def test_unread_stream_still_frees_its_slot(monkeypatch):
    monkeypatch.setitem(transfers._slots, transfers.DOWNLOAD, threading.BoundedSemaphore(1))
    assert transfers.acquire(transfers.DOWNLOAD)
    stream = transfers.ReleasingStream(type("U", (), {"read": lambda self, n: b"", "close": lambda self: None})())
    stream.close()  # e.g. the client disconnected before any byte was sent
    stream.close()  # idempotent
    assert transfers.acquire(transfers.DOWNLOAD)
    transfers.release(transfers.DOWNLOAD)


@pytest.mark.django_db
def test_busy_uploads_do_not_block_downloads(auth_client, subscribed_user, monkeypatch):
    from apps.storage.models import Upload

    monkeypatch.setitem(transfers._slots, transfers.UPLOAD, threading.BoundedSemaphore(1))
    assert transfers.acquire(transfers.UPLOAD)  # every upload slot is taken
    try:
        upload = Upload.objects.create(
            user=subscribed_user, upload_id="u", object_key="k-busy", spacebyte_upload_id="sb", spacebyte_key="k",
            encrypted_name="ZW5j", name_nonce="00", expected_size_bytes=10, part_size=1024,
            status=Upload.STATUS_UPLOADING, expires_at="2099-01-01T00:00:00Z",
        )
        res = auth_client.post(f"/api/v1/uploads/{upload.id}/parts/1", data=b"\0" * 26, content_type="application/octet-stream")
        assert res.status_code == 503
        assert transfers.acquire(transfers.DOWNLOAD)  # downloads have their own slots
        transfers.release(transfers.DOWNLOAD)
    finally:
        transfers.release(transfers.UPLOAD)
