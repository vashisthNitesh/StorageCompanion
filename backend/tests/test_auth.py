import pytest
from apps.accounts.models import User, Session


@pytest.mark.django_db
def test_register_and_login_flow(api_client):
    # Register
    reg_payload = {
        "email": "newuser@speedcloud.local",
        "password": "SecurePassword2026!",
        "full_name": "New User",
        "wrapped_master_key": "wrapped_key_test_blob",
        "kdf_salt": "salt123456",
        "kdf_params": {"m": 65536, "t": 3, "p": 4},
        "public_key": "x25519_pub_test",
        "wrapped_private_key": "wrapped_priv_test",
        "recovery_wrapped_master_key": "recovery_blob_test",
    }
    res = api_client.post("/api/v1/auth/register", reg_payload, format="json")
    assert res.status_code == 201
    assert "access_token" in res.data
    assert res.cookies.get("refresh_token") is not None

    user = User.objects.get(email="newuser@speedcloud.local")
    assert user.wrapped_master_key == "wrapped_key_test_blob"
    assert user.check_password("SecurePassword2026!")

    # Login
    login_payload = {
        "email": "newuser@speedcloud.local",
        "password": "SecurePassword2026!",
    }
    res2 = api_client.post("/api/v1/auth/login", login_payload, format="json")
    assert res2.status_code == 200
    assert "access_token" in res2.data
    assert res2.cookies.get("refresh_token") is not None


@pytest.mark.django_db
def test_refresh_token_cookie_rotation(api_client, subscribed_user):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(subscribed_user)

    api_client.cookies["refresh_token"] = str(refresh)
    res = api_client.post("/api/v1/auth/refresh")
    assert res.status_code == 200
    assert "access_token" in res.data
    assert api_client.cookies.get("refresh_token") is not None
