import pyotp
from django.conf import settings
from django.contrib.auth import authenticate
from rest_framework import status, permissions, generics
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from apps.accounts.models import User, Session
from apps.accounts.serializers import (
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
    SessionSerializer,
    ChangePasswordSerializer,
    GoogleAuthSerializer,
    VaultSetupSerializer,
)
from apps.accounts.services import (
    register_user,
    issue_session_tokens,
    rotate_refresh_token,
    revoke_session,
    revoke_other_sessions,
    setup_totp_mfa,
    check_mfa_for_login,
    verify_totp_code,
    ensure_not_locked_out,
    record_failed_auth,
    clear_failed_auth,
    verify_google_credential,
    resolve_google_user,
    google_vault_key_for,
)
from apps.audit.models import AuditLog


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    cookie_name = settings.SIMPLE_JWT["AUTH_COOKIE"]
    max_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
    response.set_cookie(
        key=cookie_name,
        value=refresh_token,
        max_age=max_age,
        httponly=settings.SIMPLE_JWT["AUTH_COOKIE_HTTP_ONLY"],
        samesite=settings.SIMPLE_JWT["AUTH_COOKIE_SAMESITE"],
        secure=settings.SIMPLE_JWT["AUTH_COOKIE_SECURE"],
        path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
    )


def clear_refresh_cookie(response: Response) -> None:
    cookie_name = settings.SIMPLE_JWT["AUTH_COOKIE"]
    response.delete_cookie(
        key=cookie_name,
        path=settings.SIMPLE_JWT["AUTH_COOKIE_PATH"],
    )


def current_session_id(request) -> str | None:
    token = getattr(request, "auth", None)
    return token.get("sid") if token is not None else None


def resolve_login_email(identifier: str) -> str:
    """Accepts a full email or the part before "@" (e.g. an admin username)."""
    identifier = identifier.strip()
    if "@" in identifier:
        return identifier.lower()
    matched = User.objects.filter(email__istartswith=f"{identifier}@").values_list("email", flat=True).first()
    return matched or identifier.lower()


class AuthThrottleMixin:
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class RegisterView(AuthThrottleMixin, APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user, refresh = register_user(
            email=data["email"],
            password=data["password"],
            full_name=data.get("full_name", ""),
            wrapped_master_key=data["wrapped_master_key"],
            kdf_salt=data["kdf_salt"],
            kdf_params=data["kdf_params"],
            public_key=data["public_key"],
            wrapped_private_key=data["wrapped_private_key"],
            recovery_wrapped_master_key=data["recovery_wrapped_master_key"],
            request=request,
        )

        response = Response(
            {
                "success": True,
                "message": "Account created successfully.",
                "user": UserSerializer(user).data,
                "access_token": str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )
        set_refresh_cookie(response, str(refresh))
        return response


class LoginView(AuthThrottleMixin, APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = resolve_login_email(serializer.validated_data["email"])
        password = serializer.validated_data["password"]
        totp_code = serializer.validated_data.get("totp_code")

        ensure_not_locked_out(email)
        user = authenticate(request, username=email, password=password)
        if user is None:
            record_failed_auth(email)
            return Response({"error": "Invalid email or password."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            if not check_mfa_for_login(user, totp_code):
                return Response(
                    {"success": False, "mfa_required": True, "message": "Enter the code from your authenticator app."},
                    status=status.HTTP_200_OK,
                )
        except AuthenticationFailed as e:
            return Response({"error": str(e.detail)}, status=status.HTTP_400_BAD_REQUEST)

        clear_failed_auth(email)
        refresh, _ = issue_session_tokens(user, request)
        response = Response(
            {
                "success": True,
                "user": UserSerializer(user).data,
                "access_token": str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
        )
        set_refresh_cookie(response, str(refresh))
        return response


class RefreshTokenView(AuthThrottleMixin, APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_scope = "refresh"

    def post(self, request):
        cookie_name = settings.SIMPLE_JWT["AUTH_COOKIE"]
        refresh_token = request.COOKIES.get(cookie_name)

        if not refresh_token:
            return Response(
                {"error": "Refresh token not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            user, new_refresh = rotate_refresh_token(refresh_token)
        except AuthenticationFailed as e:
            response = Response({"error": str(e.detail)}, status=status.HTTP_401_UNAUTHORIZED)
            clear_refresh_cookie(response)
            return response

        response = Response({
            "access_token": str(new_refresh.access_token),
            "user": UserSerializer(user).data,
        })
        set_refresh_cookie(response, str(new_refresh))
        return response


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        session = Session.objects.filter(id=current_session_id(request), user=request.user).first()
        if session:
            revoke_session(session)

        cookie_name = settings.SIMPLE_JWT["AUTH_COOKIE"]
        refresh_token = request.COOKIES.get(cookie_name)
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass

        AuditLog.objects.create(
            user=request.user,
            action="auth.logout",
            target_type="user",
            target_id=str(request.user.id),
        )

        response = Response({"success": True, "message": "Logged out successfully."})
        clear_refresh_cookie(response)
        return response


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class ChangePasswordView(AuthThrottleMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user
        if not user.check_password(data["current_password"]):
            return Response(
                {"error": "Current password does not match."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update password & re-wrapped master key if provided
        user.set_password(data["new_password"])
        if data.get("new_wrapped_master_key"):
            user.wrapped_master_key = data["new_wrapped_master_key"]
        if data.get("new_kdf_salt"):
            user.kdf_salt = data["new_kdf_salt"]
        if data.get("new_kdf_params"):
            user.kdf_params = data["new_kdf_params"]
        user.save()

        # Sign out every other device that knew the old password.
        revoked = revoke_other_sessions(user, keep_session_id=current_session_id(request))

        AuditLog.objects.create(
            user=user,
            action="user.password_changed",
            target_type="user",
            target_id=str(user.id),
            metadata={"sessions_revoked": revoked},
        )

        return Response({"success": True, "message": "Password updated. Other devices have been signed out."})


class VaultSetupView(AuthThrottleMixin, APIView):
    """
    One-time vault creation for password accounts that do not have one yet (for example
    accounts created by an administrator). The browser generates and wraps the keys.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.wrapped_master_key:
            return Response({"error": "This account already has a vault."}, status=status.HTTP_400_BAD_REQUEST)
        if not user.has_usable_password() or not user.check_password(request.data.get("password") or ""):
            return Response({"error": "Invalid password."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = VaultSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(user, field, value)
        user.save(update_fields=list(serializer.validated_data.keys()))
        AuditLog.objects.create(user=user, action="vault.created", target_type="user", target_id=str(user.id))
        return Response({"success": True, "user": UserSerializer(user).data})


class GoogleVaultKeyView(APIView):
    """
    Returns the server-derived vault key of an account created with Google sign-in, so a
    new browser tab of an authenticated session can open the vault. Accounts with a
    password-protected vault never get a key from the server.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        key = google_vault_key_for(request.user)
        if not key:
            return Response({"error": "This account's vault is unlocked with its password."}, status=status.HTTP_404_NOT_FOUND)
        response = Response({"oauth_vault_hex": key})
        response["Cache-Control"] = "no-store"
        return response


class MFAEnrollView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        device_data = setup_totp_mfa(request.user)
        return Response(device_data)


class MFAVerifyView(AuthThrottleMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        code = (request.data.get("code") or "").replace(" ", "")
        if not code:
            return Response({"error": "Verification code is required."}, status=400)

        device = request.user.mfa_devices.filter(confirmed=False).first()
        if not device:
            return Response({"error": "No pending MFA setup found."}, status=400)

        totp = pyotp.TOTP(device.secret)
        if totp.verify(code, valid_window=1):
            device.confirmed = True
            device.save()
            request.user.mfa_enabled = True
            request.user.save(update_fields=["mfa_enabled"])

            AuditLog.objects.create(
                user=request.user,
                action="mfa.enabled",
                target_type="user",
                target_id=str(request.user.id),
            )
            return Response({"success": True, "message": "MFA enabled successfully."})

        return Response({"error": "Invalid verification code."}, status=400)


class MFADisableView(AuthThrottleMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.has_usable_password():
            password = request.data.get("password")
            if not password or not user.check_password(password):
                return Response({"error": "Invalid password."}, status=400)
        elif not verify_totp_code(user, request.data.get("code") or ""):
            # Google-only accounts have no password; they confirm with a current 2FA code.
            return Response({"error": "Invalid verification code."}, status=400)

        request.user.mfa_enabled = False
        request.user.save(update_fields=["mfa_enabled"])
        request.user.mfa_devices.all().delete()

        AuditLog.objects.create(
            user=request.user,
            action="mfa.disabled",
            target_type="user",
            target_id=str(request.user.id),
        )
        return Response({"success": True, "message": "MFA has been disabled."})


class SessionListView(generics.ListAPIView):
    serializer_class = SessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return Session.objects.filter(user=self.request.user, revoked_at__isnull=True)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        current = current_session_id(request)
        for item in response.data:
            item["is_current"] = str(item["id"]) == str(current)
        return response


class SessionRevokeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, session_id):
        session = Session.objects.filter(id=session_id, user=request.user).first()
        if not session:
            return Response({"error": "Session not found."}, status=404)

        revoke_session(session)

        AuditLog.objects.create(
            user=request.user,
            action="session.revoked",
            target_type="session",
            target_id=str(session.id),
        )
        return Response({"success": True, "message": "Session revoked."})


class GoogleAuthView(AuthThrottleMixin, APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        credential = serializer.validated_data["credential"]
        totp_code = serializer.validated_data.get("totp_code")

        payload = verify_google_credential(credential)
        ensure_not_locked_out(payload["email"])
        user, is_new = resolve_google_user(payload)

        try:
            if not check_mfa_for_login(user, totp_code):
                return Response(
                    {"success": False, "mfa_required": True, "message": "Enter the code from your authenticator app."},
                    status=status.HTTP_200_OK,
                )
        except AuthenticationFailed as e:
            return Response({"error": str(e.detail)}, status=status.HTTP_400_BAD_REQUEST)

        clear_failed_auth(user.email)
        refresh, _ = issue_session_tokens(
            user, request, audit_action="user.registered_google" if is_new else "auth.google_login"
        )

        response = Response(
            {
                "success": True,
                "user": UserSerializer(user).data,
                "access_token": str(refresh.access_token),
                "oauth_vault_hex": google_vault_key_for(user),
            },
            status=status.HTTP_200_OK,
        )
        set_refresh_cookie(response, str(refresh))
        return response


class AuthConfigView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({
            "google_client_id": getattr(settings, "GOOGLE_CLIENT_ID", ""),
            "payments_enabled": bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET),
        })
