from django.urls import path
from apps.accounts.views import (
    RegisterView,
    LoginView,
    RefreshTokenView,
    LogoutView,
    MeView,
    ChangePasswordView,
    MFAEnrollView,
    MFAVerifyView,
    MFADisableView,
    SessionListView,
    SessionRevokeView,
    GoogleAuthView,
    AuthConfigView,
    VaultSetupView,
    GoogleVaultKeyView,
)

urlpatterns = [
    path("register", RegisterView.as_view(), name="auth-register"),
    path("login", LoginView.as_view(), name="auth-login"),
    path("google", GoogleAuthView.as_view(), name="auth-google"),
    path("config", AuthConfigView.as_view(), name="auth-config"),
    path("refresh", RefreshTokenView.as_view(), name="auth-refresh"),
    path("logout", LogoutView.as_view(), name="auth-logout"),
    path("me", MeView.as_view(), name="auth-me"),
    path("password", ChangePasswordView.as_view(), name="auth-password"),
    path("vault", VaultSetupView.as_view(), name="auth-vault-setup"),
    path("vault/google-key", GoogleVaultKeyView.as_view(), name="auth-vault-google-key"),
    path("mfa/enroll", MFAEnrollView.as_view(), name="auth-mfa-enroll"),
    path("mfa/verify", MFAVerifyView.as_view(), name="auth-mfa-verify"),
    path("mfa/disable", MFADisableView.as_view(), name="auth-mfa-disable"),
    path("sessions", SessionListView.as_view(), name="auth-sessions"),
    path("sessions/<uuid:session_id>", SessionRevokeView.as_view(), name="auth-session-revoke"),
]

