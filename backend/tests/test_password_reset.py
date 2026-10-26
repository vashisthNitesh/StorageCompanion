"""Auth keys, recovery keys and password reset. The server only ever sees derived keys and hashes."""
import hashlib
import re
from datetime import datetime, timedelta
from unittest import mock

import pytest
from django.core import mail
from rest_framework.test import APIClient

from apps.accounts.credentials import reset_tokens
from apps.accounts.models import Session, User
from tests.conftest import bearer_client_for

AUTH_KEY = "a1" * 32
NEW_AUTH_KEY = "e5" * 32
RECOVERY_AUTH = "7f" * 32
RECOVERY_HASH = hashlib.sha256(bytes.fromhex(RECOVERY_AUTH)).hexdigest()


@pytest.fixture
def vault_user(db):
    """An upgraded account with a confirmed recovery key."""
    from django.utils import timezone

    return User.objects.create_user(
        email="vault@example.com",
        password=AUTH_KEY,
        auth_scheme=User.AUTH_SCHEME_AUTH_KEY,
        wrapped_master_key="wmk-old",
        kdf_salt="00" * 16,
        kdf_params={"iterations": 3, "memorySize": 65536, "parallelism": 4, "hashLength": 32},
        public_key="pk-old",
        wrapped_private_key="wpk-old",
        recovery_wrapped_master_key="rwmk",
        recovery_auth_hash=RECOVERY_HASH,
        recovery_key_confirmed_at=timezone.now(),
    )


def reset_link(user):
    mail.outbox.clear()
    APIClient().post("/api/v1/auth/password-reset", {"email": user.email}, format="json")
    assert len(mail.outbox) == 1
    match = re.search(r"/reset-password#uid=([^&\s]+)&token=(\S+)", mail.outbox[0].body)
    assert match, mail.outbox[0].body
    return {"uid": match.group(1), "token": match.group(2)}


def new_vault(**extra):
    return {
        "auth_key": NEW_AUTH_KEY,
        "wrapped_master_key": "wmk-new",
        "kdf_salt": "11" * 16,
        "kdf_params": {"iterations": 3, "memorySize": 65536, "parallelism": 4, "hashLength": 32},
        **extra,
    }


# -- Prelogin and sign-in ---------------------------------------------------

@pytest.mark.django_db
def test_prelogin_does_not_reveal_unknown_accounts(api_client, vault_user):
    known = api_client.post("/api/v1/auth/prelogin", {"email": vault_user.email}, format="json").data
    assert known == {"scheme": "auth_key", "kdf_salt": vault_user.kdf_salt, "kdf_params": vault_user.kdf_params}

    unknown = api_client.post("/api/v1/auth/prelogin", {"email": "nobody@example.com"}, format="json").data
    again = api_client.post("/api/v1/auth/prelogin", {"email": "nobody@example.com"}, format="json").data
    assert unknown["scheme"] == "auth_key" and len(unknown["kdf_salt"]) == 32 and unknown == again


@pytest.mark.django_db
def test_staff_sign_in_with_a_password(api_client):
    User.objects.create_superuser(email="boss@example.com", password="AdminPassword123!")
    assert api_client.post("/api/v1/auth/prelogin", {"email": "boss@example.com"}, format="json").data["scheme"] == "password"
    res = api_client.post("/api/v1/auth/login", {"email": "boss@example.com", "password": "AdminPassword123!"}, format="json")
    assert res.status_code == 200


@pytest.mark.django_db
def test_auth_key_accounts_reject_the_plain_password(api_client, vault_user):
    assert api_client.post("/api/v1/auth/login", {"email": vault_user.email, "password": AUTH_KEY}, format="json").status_code == 400
    assert api_client.post("/api/v1/auth/login", {"email": vault_user.email, "auth_key": AUTH_KEY}, format="json").status_code == 200


@pytest.mark.django_db
def test_legacy_account_is_upgraded_on_next_sign_in(api_client, subscribed_user):
    assert api_client.post("/api/v1/auth/prelogin", {"email": subscribed_user.email}, format="json").data["scheme"] == "password"
    res = api_client.post(
        "/api/v1/auth/login",
        {"email": subscribed_user.email, "password": "TestPassword123!", "auth_key": AUTH_KEY},
        format="json",
    )
    assert res.status_code == 200
    subscribed_user.refresh_from_db()
    assert subscribed_user.auth_scheme == "auth_key"
    assert not subscribed_user.check_password("TestPassword123!")
    # From now on the password alone no longer works; the derived key does.
    assert APIClient().post("/api/v1/auth/login", {"email": subscribed_user.email, "password": "TestPassword123!"}, format="json").status_code == 400
    assert APIClient().post("/api/v1/auth/login", {"email": subscribed_user.email, "auth_key": AUTH_KEY}, format="json").status_code == 200


@pytest.mark.django_db
def test_profile_never_exposes_the_recovery_hash(vault_user):
    data = bearer_client_for(vault_user).get("/api/v1/auth/me").data
    assert data["has_recovery_key"] is True
    assert "recovery_auth_hash" not in data and "password" not in data


# -- Recovery key -------------------------------------------------------------

@pytest.mark.django_db
def test_recovery_key_from_sign_up_is_confirmed_once_saved(api_client):
    from tests.test_auth import REGISTER_PAYLOAD

    res = api_client.post("/api/v1/auth/register", REGISTER_PAYLOAD, format="json")
    assert res.data["user"]["has_recovery_key"] is False
    user = User.objects.get(email=REGISTER_PAYLOAD["email"])
    confirmed = bearer_client_for(user).post("/api/v1/auth/recovery-key/confirm")
    assert confirmed.status_code == 200 and confirmed.data["user"]["has_recovery_key"] is True


@pytest.mark.django_db
def test_replacing_the_recovery_key_needs_the_current_password(vault_user):
    client = bearer_client_for(vault_user)
    body = {"recovery_wrapped_master_key": "rwmk-2", "recovery_auth_hash": "ab" * 32}
    assert client.put("/api/v1/auth/recovery-key", body, format="json").status_code == 400
    assert client.put("/api/v1/auth/recovery-key", {**body, "auth_key": "00" * 32}, format="json").status_code == 400
    assert client.put("/api/v1/auth/recovery-key", {**body, "auth_key": AUTH_KEY}, format="json").status_code == 200
    vault_user.refresh_from_db()
    assert vault_user.recovery_wrapped_master_key == "rwmk-2" and vault_user.recovery_auth_hash == "ab" * 32


# -- Forgot password ------------------------------------------------------------

@pytest.mark.django_db
def test_reset_request_looks_the_same_for_unknown_emails(api_client, vault_user):
    res = api_client.post("/api/v1/auth/password-reset", {"email": "nobody@example.com"}, format="json")
    assert res.status_code == 200 and len(mail.outbox) == 0
    res = api_client.post("/api/v1/auth/password-reset", {"email": vault_user.email}, format="json")
    assert res.status_code == 200 and len(mail.outbox) == 1
    assert "30 minutes" in mail.outbox[0].body


@pytest.mark.django_db
def test_staff_cannot_reset_by_email(api_client):
    User.objects.create_superuser(email="boss@example.com", password="AdminPassword123!")
    api_client.post("/api/v1/auth/password-reset", {"email": "boss@example.com"}, format="json")
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_reset_emails_are_rate_limited_per_address(vault_user):
    codes = [APIClient().post("/api/v1/auth/password-reset", {"email": vault_user.email}, format="json").status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]


@pytest.mark.django_db
def test_check_returns_the_recovery_wrap_only_for_a_valid_link(api_client, vault_user):
    link = reset_link(vault_user)
    res = api_client.post("/api/v1/auth/password-reset/check", link, format="json")
    assert res.status_code == 200
    assert res.data["has_recovery_key"] is True and res.data["recovery_wrapped_master_key"] == "rwmk"
    bad = api_client.post("/api/v1/auth/password-reset/check", {**link, "token": "x-y"}, format="json")
    assert bad.status_code == 400 and bad.data["code"] == "RESET_LINK_INVALID"


@pytest.mark.django_db
def test_reset_link_expires_after_30_minutes(api_client, vault_user):
    link = reset_link(vault_user)
    later = datetime.now() + timedelta(minutes=31)
    with mock.patch.object(reset_tokens, "_now", return_value=later):
        res = api_client.post("/api/v1/auth/password-reset/check", link, format="json")
    assert res.status_code == 400


@pytest.mark.django_db
def test_reset_with_recovery_key_rewraps_and_works_once(api_client, vault_user):
    other_device = bearer_client_for(vault_user)
    link = reset_link(vault_user)

    wrong = api_client.post(
        "/api/v1/auth/password-reset/complete", {**link, "mode": "recovery", "recovery_auth": "00" * 32, **new_vault()}, format="json"
    )
    assert wrong.status_code == 400 and wrong.data["code"] == "RECOVERY_KEY_MISMATCH"
    vault_user.refresh_from_db()
    assert vault_user.wrapped_master_key == "wmk-old"

    ok = api_client.post(
        "/api/v1/auth/password-reset/complete", {**link, "mode": "recovery", "recovery_auth": RECOVERY_AUTH, **new_vault()}, format="json"
    )
    assert ok.status_code == 200, ok.content
    vault_user.refresh_from_db()
    assert vault_user.check_password(NEW_AUTH_KEY) and not vault_user.check_password(AUTH_KEY)
    assert vault_user.wrapped_master_key == "wmk-new" and vault_user.kdf_salt == "11" * 16
    # Same master key, so the recovery key and the sharing keys stay valid.
    assert vault_user.recovery_wrapped_master_key == "rwmk" and vault_user.has_recovery_key
    assert vault_user.public_key == "pk-old"
    # Every device is signed out, and the link can't be used again.
    assert not Session.objects.filter(user=vault_user, revoked_at__isnull=True).exists()
    assert other_device.get("/api/v1/auth/me").status_code == 401
    again = api_client.post(
        "/api/v1/auth/password-reset/complete", {**link, "mode": "recovery", "recovery_auth": RECOVERY_AUTH, **new_vault()}, format="json"
    )
    assert again.status_code == 400


@pytest.mark.django_db
def test_reset_without_recovery_key_needs_explicit_confirmation(api_client, vault_user):
    link = reset_link(vault_user)
    body = {**link, "mode": "reset", **new_vault(public_key="pk-new", wrapped_private_key="wpk-new")}
    refused = api_client.post("/api/v1/auth/password-reset/complete", body, format="json")
    assert refused.status_code == 400

    ok = api_client.post("/api/v1/auth/password-reset/complete", {**body, "confirm_data_loss": True}, format="json")
    assert ok.status_code == 200
    vault_user.refresh_from_db()
    assert vault_user.check_password(NEW_AUTH_KEY)
    assert vault_user.wrapped_master_key == "wmk-new" and vault_user.public_key == "pk-new"
    # The old recovery key no longer applies; the user is asked to make a new one after signing in.
    assert not vault_user.has_recovery_key and vault_user.recovery_wrapped_master_key == ""


# -- Change password -----------------------------------------------------------

@pytest.mark.django_db
def test_change_password_rewraps_with_auth_keys(vault_user):
    client = bearer_client_for(vault_user)
    body = {
        "new_auth_key": NEW_AUTH_KEY,
        "new_wrapped_master_key": "wmk-new",
        "new_kdf_salt": "22" * 16,
        "new_kdf_params": {"iterations": 3, "memorySize": 65536, "parallelism": 4, "hashLength": 32},
    }
    assert client.post("/api/v1/auth/password", {**body, "current_auth_key": "00" * 32}, format="json").status_code == 400
    assert client.post("/api/v1/auth/password", {**body, "current_password": AUTH_KEY}, format="json").status_code == 400
    missing = client.post("/api/v1/auth/password", {"current_auth_key": AUTH_KEY, "new_auth_key": NEW_AUTH_KEY}, format="json")
    assert missing.status_code == 400

    assert client.post("/api/v1/auth/password", {**body, "current_auth_key": AUTH_KEY}, format="json").status_code == 200
    vault_user.refresh_from_db()
    assert vault_user.check_password(NEW_AUTH_KEY) and vault_user.wrapped_master_key == "wmk-new"
    assert vault_user.kdf_salt == "22" * 16


@pytest.mark.django_db
def test_mfa_disable_accepts_the_auth_key(vault_user):
    vault_user.mfa_enabled = True
    vault_user.save()
    client = bearer_client_for(vault_user)
    assert client.post("/api/v1/auth/mfa/disable", {"password": AUTH_KEY}, format="json").status_code == 400
    assert client.post("/api/v1/auth/mfa/disable", {"auth_key": AUTH_KEY}, format="json").status_code == 200
