import pyotp
import pytest


@pytest.mark.django_db
def test_mfa_enroll_verify_and_reenroll_blocked(auth_client, subscribed_user):
    res = auth_client.post("/api/v1/auth/mfa/enroll")
    assert res.status_code == 200
    assert res.data["qr_code"].startswith("data:image/png;base64,")
    assert len(res.data["backup_codes"]) == 10

    code = pyotp.TOTP(res.data["secret"]).now()
    assert auth_client.post("/api/v1/auth/mfa/verify", {"code": code}, format="json").status_code == 200
    subscribed_user.refresh_from_db()
    assert subscribed_user.mfa_enabled

    # Re-enrolling must not silently replace the confirmed device (lockout)
    assert auth_client.post("/api/v1/auth/mfa/enroll").status_code == 400
    assert subscribed_user.mfa_devices.filter(confirmed=True).count() == 1


@pytest.mark.django_db
def test_mfa_disable_requires_password(auth_client, subscribed_user):
    res = auth_client.post("/api/v1/auth/mfa/enroll")
    auth_client.post("/api/v1/auth/mfa/verify", {"code": pyotp.TOTP(res.data["secret"]).now()}, format="json")
    assert auth_client.post("/api/v1/auth/mfa/disable", {"password": "wrong"}, format="json").status_code == 400
    subscribed_user.refresh_from_db()
    assert subscribed_user.mfa_enabled
