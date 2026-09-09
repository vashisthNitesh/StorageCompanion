from django.urls import path
from apps.accounts.admin_views import (
    AdminKPIsView,
    AdminPoolStatusView,
    AdminUsersListView,
    AdminUserPlanUpgradeView,
    AdminUserStatusToggleView,
)

urlpatterns = [
    path("kpis/", AdminKPIsView.as_view(), name="admin-kpis"),
    path("pool/", AdminPoolStatusView.as_view(), name="admin-pool"),
    path("users/", AdminUsersListView.as_view(), name="admin-users"),
    path("users/<uuid:user_id>/upgrade-plan/", AdminUserPlanUpgradeView.as_view(), name="admin-user-upgrade-plan"),
    path("users/<uuid:user_id>/toggle-status/", AdminUserStatusToggleView.as_view(), name="admin-user-toggle-status"),
]
