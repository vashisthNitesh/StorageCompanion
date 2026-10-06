import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.billing.models import Plan, Subscription
from apps.storage.models import StorageQuota


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
        price_yearly=1999.00,
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
    from datetime import timedelta

    from django.utils import timezone
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
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(subscribed_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


class FakeS3Client:
    """Offline stand-in for boto3's S3 client so tests never touch a real/local object store."""

    def create_multipart_upload(self, Bucket, Key, **kw):
        return {"UploadId": "mock-upload-test"}

    def generate_presigned_url(self, ClientMethod, Params, ExpiresIn=900):
        q = "&".join(f"{k}={v}" for k, v in Params.items())
        return f"https://mock-s3.local/{ClientMethod}?{q}"

    def list_parts(self, **kw):
        return {"Parts": []}

    def complete_multipart_upload(self, **kw):
        return {}

    def abort_multipart_upload(self, **kw):
        return {}

    def get_object(self, **kw):
        raise ConnectionError("fake s3: no object storage in tests")


@pytest.fixture(autouse=True)
def fake_s3(monkeypatch):
    fake = FakeS3Client()
    for target in ("apps.storage.services", "apps.storage.views", "apps.sharing.services", "apps.sharing.views"):
        monkeypatch.setattr(f"{target}.get_s3_client", lambda: fake, raising=False)
    return fake


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()
