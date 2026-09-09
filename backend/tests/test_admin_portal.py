import pytest
from rest_framework.test import APIClient
from django.core.management import call_command
from apps.accounts.models import User
from apps.billing.models import Plan, Subscription
from apps.storage.models import StorageQuota


@pytest.mark.django_db
def test_superuser_creation_and_login():
    call_command("create_master_admin")

    client = APIClient()

    # 1. Login with username 'nitesh-vashisth'
    res_user = client.post(
        "/api/v1/auth/login",
        {"email": "nitesh-vashisth", "password": "vashisth@0000"},
        format="json",
    )
    assert res_user.status_code == 200
    assert res_user.data["user"]["is_staff"] is True
    assert res_user.data["user"]["is_superuser"] is True
    assert "access_token" in res_user.data

    # 2. Login with email 'nitesh-vashisth@smartspacedata.com'
    res_email = client.post(
        "/api/v1/auth/login",
        {"email": "nitesh-vashisth@smartspacedata.com", "password": "vashisth@0000"},
        format="json",
    )
    assert res_email.status_code == 200


@pytest.mark.django_db
def test_regular_user_blocked_from_admin_endpoints(subscribed_user):
    client = APIClient()
    client.force_authenticate(user=subscribed_user)

    # All admin endpoints return 403 Forbidden for non-staff
    assert client.get("/api/v1/admin/kpis/").status_code == 403
    assert client.get("/api/v1/admin/pool/").status_code == 403
    assert client.get("/api/v1/admin/users/").status_code == 403
    assert client.post(f"/api/v1/admin/users/{subscribed_user.id}/upgrade-plan/", {}).status_code == 403
    assert client.post(f"/api/v1/admin/users/{subscribed_user.id}/toggle-status/").status_code == 403


@pytest.mark.django_db
def test_admin_kpis_and_periods(subscribed_user):
    call_command("create_master_admin")
    admin_user = User.objects.get(email="nitesh-vashisth@smartspacedata.com")

    client = APIClient()
    client.force_authenticate(user=admin_user)

    # Test each timeframe: daily, weekly, monthly, yearly
    for period in ["daily", "weekly", "monthly", "yearly"]:
        res = client.get(f"/api/v1/admin/kpis/?period={period}")
        assert res.status_code == 200
        data = res.json()
        assert data["period"] == period
        assert "kpis" in data
        assert "total_users" in data["kpis"]
        assert "active_users" in data["kpis"]
        assert "pool_used_gb" in data["kpis"]
        assert "plan_distribution" in data
        assert "activity_trend" in data
        assert "recent_activity" in data


@pytest.mark.django_db
def test_admin_pool_status():
    call_command("create_master_admin")
    admin_user = User.objects.get(email="nitesh-vashisth@smartspacedata.com")

    client = APIClient()
    client.force_authenticate(user=admin_user)

    res = client.get("/api/v1/admin/pool/")
    assert res.status_code == 200
    data = res.json()
    assert "total_pool_bytes" in data
    assert "pool_health" in data
    assert "expansion_tiers" in data
    assert len(data["expansion_tiers"]) >= 3


@pytest.mark.django_db
def test_admin_user_management_and_upgrade(subscribed_user):
    call_command("seed_demo")
    call_command("create_master_admin")
    admin_user = User.objects.get(email="nitesh-vashisth@smartspacedata.com")

    client = APIClient()
    client.force_authenticate(user=admin_user)

    # 1. User list (strictly customers, admin excluded)
    res_list = client.get("/api/v1/admin/users/")
    assert res_list.status_code == 200
    assert res_list.json()["total_count"] >= 1
    user_emails = [u["email"] for u in res_list.json()["results"]]
    assert admin_user.email not in user_emails
    assert subscribed_user.email in user_emails

    # Search user
    res_search = client.get(f"/api/v1/admin/users/?search={subscribed_user.email}")
    assert res_search.status_code == 200
    assert len(res_search.json()["results"]) == 1

    # 2. Upgrade user plan to Mega Pack
    res_upgrade = client.post(
        f"/api/v1/admin/users/{subscribed_user.id}/upgrade-plan/",
        {
            "plan_code": "mega",
            "billing_interval": "yearly",
            "custom_limit_gb": 1000,
        },
        format="json",
    )
    assert res_upgrade.status_code == 200
    assert res_upgrade.json()["success"] is True

    # Verify quota updated
    quota = StorageQuota.objects.get(user=subscribed_user)
    assert quota.bytes_limit == 1000 * 1024 * 1024 * 1024

    # Verify subscription updated
    sub = Subscription.objects.get(user=subscribed_user)
    assert sub.plan.code == "mega"
    assert sub.billing_interval == "yearly"

    # 3. Toggle user status (suspend)
    res_toggle = client.post(f"/api/v1/admin/users/{subscribed_user.id}/toggle-status/")
    assert res_toggle.status_code == 200
    assert res_toggle.json()["is_active"] is False

    subscribed_user.refresh_from_db()
    assert subscribed_user.is_active is False


@pytest.mark.django_db
def test_super_admin_has_no_pack():
    call_command("create_master_admin")
    admin_user = User.objects.get(email="nitesh-vashisth@smartspacedata.com")

    # Super admin does not have a customer subscription
    assert not Subscription.objects.filter(user=admin_user).exists()
    quota = StorageQuota.objects.get(user=admin_user)
    assert quota.bytes_limit == 0
    assert quota.bytes_used == 0

    # Pool stats show 0 GB used by admin
    stats = StorageQuota.get_global_pool_stats()
    assert stats["used_bytes"] == 0

    # Trying to assign a pack to super admin is rejected
    client = APIClient()
    client.force_authenticate(user=admin_user)
    res = client.post(
        f"/api/v1/admin/users/{admin_user.id}/upgrade-plan/",
        {"plan_code": "mega", "billing_interval": "monthly"},
        format="json",
    )
    assert res.status_code == 400
    assert "Super Admin is the platform administrator" in res.data["error"]
