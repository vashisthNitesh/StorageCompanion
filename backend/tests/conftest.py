import pytest
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.billing.models import Plan, Subscription
from apps.storage.models import StorageQuota


@pytest.fixture(autouse=True)
def _clear_cache():
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def sample_plan(db):
    return Plan.objects.create(
        code="test_personal",
        name="Test Personal",
        storage_bytes=100 * 1024 * 1024,  # 100 MB for fast testing
        price_monthly=199.00,
        currency="INR",
        max_file_size=50 * 1024 * 1024,
        is_active=True,
    )


@pytest.fixture
def subscribed_user(db, sample_plan):
    user = User.objects.create_user(
        email="testuser@speedcloud.local",
        password="TestPassword123!",
        wrapped_master_key="wrapped_master_key_test",
        kdf_salt="salt_test",
        kdf_params={"m": 65536, "t": 3, "p": 4},
        public_key="pub_key_test",
        wrapped_private_key="priv_key_test",
        recovery_wrapped_master_key="recovery_test",
    )
    from django.utils import timezone
    from datetime import timedelta
    Subscription.objects.create(
        user=user,
        plan=sample_plan,
        provider="razorpay",
        provider_subscription_id="sub_test_123",
        status="active",
        current_period_start=timezone.now(),
        current_period_end=timezone.now() + timedelta(days=30),
    )
    StorageQuota.objects.create(
        user=user,
        bytes_used=0,
        bytes_limit=sample_plan.storage_bytes,
    )
    return user




@pytest.fixture
def auth_client(api_client, subscribed_user):
    from apps.accounts.services import issue_session_tokens
    refresh, _ = issue_session_tokens(subscribed_user, audit_action=None)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


def bearer_client_for(user):
    """APIClient authenticated with a real session-bound access token for `user`."""
    from apps.accounts.services import issue_session_tokens
    client = APIClient()
    refresh, _ = issue_session_tokens(user, audit_action=None)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


def relay_all_parts(client, upload_id: str, size_bytes: int, part_size: int):
    """Relays correctly sized dummy ciphertext parts for an upload session."""
    import math
    total = max(1, math.ceil(size_bytes / part_size))
    for n in range(1, total + 1):
        plain = part_size if n < total else size_bytes - (total - 1) * part_size
        res = client.post(
            f"/api/v1/uploads/{upload_id}/parts/{n}",
            data=b"\0" * (plain + 16),
            content_type="application/octet-stream",
        )
        assert res.status_code == 200, res.content
