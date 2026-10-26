import json
import time
from unittest import mock

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User, Session
from tests.conftest import bearer_client_for

AUTH_KEY = "a1" * 32  # what the browser derives from the password; the password itself is never sent

REGISTER_PAYLOAD = {
    "email": "newuser@example.com",
    "auth_key": AUTH_KEY,
    "full_name": "New User",
    "wrapped_master_key": "wrapped_key_test_blob",
    "kdf_salt": "salt123456",
    "kdf_params": {"m": 65536, "t": 3, "p": 4},
    "public_key": "x25519_pub_test",
    "wrapped_private_key": "wrapped_priv_test",
    "recovery_wrapped_master_key": "recovery_blob_test",
    "recovery_auth_hash": "b2" * 32,
}


def google_payload(**overrides):
    payload = {
        "aud": "test-google-client-id.apps.googleusercontent.com",
        "iss": "https://accounts.google.com",
        "exp": str(int(time.time()) + 600),
        "sub": "google-sub-123",
        "email": "googletest@example.com",
        "email_verified": "true",
        "name": "Google Test",
    }
    payload.update(overrides)
    return payload


def fake_tokeninfo(payload):
    response = mock.MagicMock()
    response.read.return_value = json.dumps(payload).encode()
    response.__enter__.return_value = response
    return mock.patch("apps.accounts.services.urllib.request.urlopen", return_value=response)


@pytest.mark.django_db
def test_register_and_login_flow(api_client):
    res = api_client.post("/api/v1/auth/register", REGISTER_PAYLOAD, format="json")
    assert res.status_code == 201
    assert "access_token" in res.data
    assert res.cookies.get("refresh_token") is not None

    user = User.objects.get(email="newuser@example.com")
    assert user.wrapped_master_key == "wrapped_key_test_blob"
    assert user.check_password(AUTH_KEY)
    assert user.auth_scheme == "auth_key"

    res2 = api_client.post("/api/v1/auth/login", {"email": "newuser@example.com", "auth_key": AUTH_KEY}, format="json")
    assert res2.status_code == 200
    assert "access_token" in res2.data
    assert Session.objects.filter(user=user, revoked_at__isnull=True).count() == 2


@pytest.mark.django_db
def test_refresh_token_cookie_rotation(api_client, subscribed_user):
    from apps.accounts.services import issue_session_tokens
    refresh, session = issue_session_tokens(subscribed_user, audit_action=None)

    api_client.cookies["refresh_token"] = str(refresh)
    res = api_client.post("/api/v1/auth/refresh")
    assert res.status_code == 200
    assert res.data["user"]["email"] == subscribed_user.email
    session.refresh_from_db()
    assert session.token_jti != str(refresh["jti"])

    # The old refresh token is blacklisted after rotation
    api_client.cookies["refresh_token"] = str(refresh)
    assert api_client.post("/api/v1/auth/refresh").status_code == 401


@pytest.mark.django_db
def test_revoked_session_signs_device_out_immediately(subscribed_user):
    client = bearer_client_for(subscribed_user)
    assert client.get("/api/v1/auth/me").status_code == 200

    session = Session.objects.filter(user=subscribed_user).first()
    other = bearer_client_for(subscribed_user)
    assert other.delete(f"/api/v1/auth/sessions/{session.id}").status_code == 200

    # Access token of the revoked session no longer works, and neither does its refresh token
    assert client.get("/api/v1/auth/me").status_code == 401


@pytest.mark.django_db
def test_token_without_session_or_in_url_is_rejected(subscribed_user):
    from rest_framework_simplejwt.tokens import RefreshToken
    bare = RefreshToken.for_user(subscribed_user).access_token

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {bare}")
    assert client.get("/api/v1/auth/me").status_code == 401

    good = bearer_client_for(subscribed_user)
    token = good._credentials["HTTP_AUTHORIZATION"].split()[1]
    assert APIClient().get(f"/api/v1/auth/me?token={token}").status_code == 401
    assert APIClient().get(f"/api/v1/auth/me?access_token={token}").status_code == 401


@pytest.mark.django_db
def test_failed_logins_lock_the_account(api_client, subscribed_user):
    for _ in range(8):
        res = api_client.post(
            "/api/v1/auth/login", {"email": subscribed_user.email, "password": "wrong"}, format="json"
        )
        assert res.status_code in (400, 429)
    res = api_client.post(
        "/api/v1/auth/login", {"email": subscribed_user.email, "password": "TestPassword123!"}, format="json"
    )
    assert res.status_code == 429


@pytest.mark.django_db
def test_wrong_mfa_codes_count_towards_lockout(api_client, subscribed_user):
    import pyotp
    from apps.accounts.models import MFADevice
    MFADevice.objects.create(user=subscribed_user, secret=pyotp.random_base32(), confirmed=True)
    subscribed_user.mfa_enabled = True
    subscribed_user.save()

    creds = {"email": subscribed_user.email, "password": "TestPassword123!"}
    assert api_client.post("/api/v1/auth/login", creds, format="json").data["mfa_required"] is True
    for _ in range(8):
        api_client.post("/api/v1/auth/login", {**creds, "totp_code": "000000"}, format="json")
    res = api_client.post("/api/v1/auth/login", {**creds, "totp_code": "000000"}, format="json")
    assert res.status_code == 429


@pytest.mark.django_db
def test_google_sign_in_creates_account_with_vault_key(api_client):
    with fake_tokeninfo(google_payload()):
        res = api_client.post("/api/v1/auth/google", {"credential": "real-looking-id-token"}, format="json")
    assert res.status_code == 200
    assert len(res.data["oauth_vault_hex"]) == 64
    assert res.data["user"]["email"] == "googletest@example.com"
    assert User.objects.get(email="googletest@example.com").google_sub == "google-sub-123"


@pytest.mark.django_db
def test_mock_google_tokens_are_rejected(api_client):
    res = api_client.post("/api/v1/auth/google", {"credential": "mock_token_attacker"}, format="json")
    assert res.status_code in (401, 403)
    assert not User.objects.filter(email="attacker@example.com").exists()


@pytest.mark.django_db
@override_settings(GOOGLE_CLIENT_ID="")
def test_google_sign_in_requires_client_id(api_client):
    with fake_tokeninfo(google_payload()):
        res = api_client.post("/api/v1/auth/google", {"credential": "x"}, format="json")
    assert res.status_code in (401, 403)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "overrides",
    [
        {"aud": "someone-elses-client-id"},
        {"email_verified": "false"},
        {"iss": "https://evil.example.com"},
        {"exp": "1"},
    ],
)
def test_google_sign_in_rejects_bad_tokens(api_client, overrides):
    with fake_tokeninfo(google_payload(**overrides)):
        res = api_client.post("/api/v1/auth/google", {"credential": "x"}, format="json")
    assert res.status_code in (401, 403)


@pytest.mark.django_db
def test_google_does_not_take_over_unverified_password_account(api_client):
    api_client.post("/api/v1/auth/register", {**REGISTER_PAYLOAD, "email": "googletest@example.com"}, format="json")
    with fake_tokeninfo(google_payload()):
        res = APIClient().post("/api/v1/auth/google", {"credential": "x"}, format="json")
    assert res.status_code in (401, 403)
    assert User.objects.get(email="googletest@example.com").google_sub is None


@pytest.mark.django_db
def test_auth_config(api_client):
    res = api_client.get("/api/v1/auth/config")
    assert res.status_code == 200
    assert res.data["google_client_id"] == "test-google-client-id.apps.googleusercontent.com"
    assert res.data["payments_enabled"] is True


@pytest.mark.django_db
def test_csp_header_is_sent(api_client):
    res = api_client.get("/api/v1/health")
    assert res.status_code == 200
    assert "default-src 'self'" in res["Content-Security-Policy"]
    assert "'wasm-unsafe-eval'" in res["Content-Security-Policy"]


@pytest.mark.django_db
def test_vault_setup_only_once_and_needs_password(subscribed_user):
    subscribed_user.wrapped_master_key = ""
    subscribed_user.save()
    client = bearer_client_for(subscribed_user)
    body = {
        "wrapped_master_key": "wmk",
        "kdf_salt": "salt",
        "kdf_params": {"m": 65536, "t": 3, "p": 4},
        "public_key": "pk",
        "wrapped_private_key": "wpk",
        "recovery_wrapped_master_key": "rwmk",
        "recovery_auth_hash": "c3" * 32,
        "auth_key": "d4" * 32,
    }
    assert client.post("/api/v1/auth/vault", {**body, "password": "wrong"}, format="json").status_code == 400
    assert client.post("/api/v1/auth/vault", {**body, "password": "TestPassword123!"}, format="json").status_code == 200
    subscribed_user.refresh_from_db()
    assert subscribed_user.wrapped_master_key == "wmk"
    # The password now signs in only through the derived key.
    assert subscribed_user.auth_scheme == "auth_key" and subscribed_user.check_password("d4" * 32)
    again = client.post("/api/v1/auth/vault", {**body, "auth_key": "d4" * 32, "wrapped_master_key": "x"}, format="json")
    assert again.status_code == 400


@pytest.mark.django_db
def test_google_vault_key_only_for_google_created_accounts(api_client, subscribed_user):
    with fake_tokeninfo(google_payload()):
        res = api_client.post("/api/v1/auth/google", {"credential": "x"}, format="json")
    google_user = User.objects.get(email="googletest@example.com")
    key = bearer_client_for(google_user).get("/api/v1/auth/vault/google-key")
    assert key.status_code == 200
    assert key.data["oauth_vault_hex"] == res.data["oauth_vault_hex"]

    assert bearer_client_for(subscribed_user).get("/api/v1/auth/vault/google-key").status_code == 404
