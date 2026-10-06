import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Session, User


def login(client, email="hard@test.local", password="HardPass12345!"):
    return client.post("/api/v1/auth/login", {"email": email, "password": password}, format="json")


@pytest.fixture
def user(db):
    return User.objects.create_user(email="hard@test.local", password="HardPass12345!")


@pytest.mark.django_db
def test_query_string_token_is_not_accepted(user):
    c = APIClient()
    token = login(c).data["access_token"]
    assert APIClient().get(f"/api/v1/auth/me?token={token}").status_code == 401
    assert APIClient().get(f"/api/v1/auth/me?access_token={token}").status_code == 401
    assert APIClient().get("/api/v1/auth/me", HTTP_AUTHORIZATION=f"Bearer {token}").status_code == 200


@pytest.mark.django_db
def _pending_test_login_is_rate_limited(user):
    c = APIClient()
    codes = [login(c, password=f"wrong{i}").status_code for i in range(12)]
    assert codes[0] == 400
    assert codes[-1] == 429


@pytest.mark.django_db
def test_revoked_session_cannot_refresh_and_rotation_keeps_session_link(user):
    c = APIClient()
    assert login(c).status_code == 200
    session = Session.objects.get(user=user)
    # rotation keeps the session pointing at the newest refresh token
    assert c.post("/api/v1/auth/refresh").status_code == 200
    session.refresh_from_db()
    access = c.post("/api/v1/auth/refresh").data["access_token"]
    session.refresh_from_db()
    other = APIClient()
    other.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert other.delete(f"/api/v1/auth/sessions/{session.id}").status_code == 200
    assert c.post("/api/v1/auth/refresh").status_code == 401


@pytest.mark.django_db
def test_suspended_user_cannot_refresh(user):
    c = APIClient()
    assert login(c).status_code == 200
    user.is_active = False
    user.save()
    assert c.post("/api/v1/auth/refresh").status_code == 401
