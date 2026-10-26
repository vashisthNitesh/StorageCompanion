import pyotp
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import status, permissions, generics
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from apps.common.throttles import (
    LoginAccountThrottle,
    PasswordResetEmailThrottle,
    RefreshIPThrottle,
    RefreshSessionThrottle,
    ScopedIPThrottle,
)
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
    RecoveryKeySerializer,
    PasswordResetCompleteSerializer,
)
from apps.accounts.credentials import (
    check_sign_in_secret,
    is_hex_256,
    prelogin_params,
    reset_tokens,
    recovery_proof_matches,
    send_password_reset_email,
    set_auth_key,
    user_for_reset_token,
    uses_auth_key,
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
    throttle_classes = [ScopedIPThrottle]
    throttle_scope = "auth"


class RegisterView(AuthThrottleMixin, APIView):
    permission_classes = [permissions.AllowAny]
    throttle_scope = "register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user, refresh = register_user(
            email=data["email"],
            auth_key=data["auth_key"],
            full_name=data.get("full_name", ""),
            wrapped_master_key=data["wrapped_master_key"],
            kdf_salt=data["kdf_salt"],
            kdf_params=data["kdf_params"],
            public_key=data["public_key"],
            wrapped_private_key=data["wrapped_private_key"],
            recovery_wrapped_master_key=data["recovery_wrapped_master_key"],
            recovery_auth_hash=data["recovery_auth_hash"],
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


class PreloginView(APIView):
    """KDF salt and secret scheme for an email, so the browser can derive the auth key before signing in."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedIPThrottle]
    throttle_scope = "prelogin"

    def post(self, request):
        email = resolve_login_email(str(request.data.get("email") or ""))
        response = Response(prelogin_params(email))
        response["Cache-Control"] = "no-store"
        return response


class LoginView(AuthThrottleMixin, APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedIPThrottle, LoginAccountThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = resolve_login_email(serializer.validated_data["email"])
        password = serializer.validated_data.get("password") or ""
        auth_key = serializer.validated_data.get("auth_key") or ""
        totp_code = serializer.validated_data.get("totp_code")

        ensure_not_locked_out(email)
        account = User.objects.filter(email=email).only("auth_scheme").first()
        secret = auth_key if account is not None and uses_auth_key(account) else password
        user = authenticate(request, username=email, password=secret) if secret else None
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
        if auth_key and not uses_auth_key(user) and user.wrapped_master_key and not (user.is_staff or user.is_superuser):
            # Last time this account sends its password: from now on only the derived key.
            set_auth_key(user, auth_key)
            user.save(update_fields=["password", "auth_scheme"])
            AuditLog.objects.create(user=user, action="auth.upgraded_to_auth_key", target_type="user", target_id=str(user.id))
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


class RefreshTokenView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    # Per signed-in device, with a generous per-IP backstop (many devices can share one IP).
    throttle_classes = [RefreshSessionThrottle, RefreshIPThrottle]

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
    """
    Vault accounts send the current and new auth keys plus the master key re-wrapped in the
    browser; accounts without a vault (staff) change a plain password.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = request.user
        proof = {"auth_key": data.get("current_auth_key"), "password": data.get("current_password")}
        if not check_sign_in_secret(user, proof):
            return Response({"error": "Current password does not match."}, status=status.HTTP_400_BAD_REQUEST)

        if user.wrapped_master_key:
            if not (data.get("new_auth_key") and data.get("new_wrapped_master_key") and data.get("new_kdf_salt") and data.get("new_kdf_params")):
                return Response({"error": "Missing the re-encrypted vault key."}, status=status.HTTP_400_BAD_REQUEST)
            set_auth_key(user, data["new_auth_key"])
            user.wrapped_master_key = data["new_wrapped_master_key"]
            user.kdf_salt = data["new_kdf_salt"]
            user.kdf_params = data["new_kdf_params"]
        else:
            new_password = data.get("new_password") or ""
            try:
                validate_password(new_password, user)
            except DjangoValidationError as e:
                return Response({"error": " ".join(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(new_password)
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

        return Response({"success": True, "message": "Password updated. Other devices have been signed out.", "user": UserSerializer(user).data})


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
        if not check_sign_in_secret(user, request.data):
            return Response({"error": "Invalid password."}, status=status.HTTP_400_BAD_REQUEST)
        auth_key = request.data.get("auth_key")
        if not is_hex_256(auth_key):
            return Response({"error": "Invalid key."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = VaultSetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        for field, value in serializer.validated_data.items():
            setattr(user, field, value)
        # The vault's password now signs in through the derived key.
        set_auth_key(user, auth_key)
        user.save(update_fields=[*serializer.validated_data.keys(), "password", "auth_scheme"])
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
            if not check_sign_in_secret(user, request.data):
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
    throttle_classes = []  # static public configuration

    def get(self, request):
        return Response({
            "google_client_id": getattr(settings, "GOOGLE_CLIENT_ID", ""),
            "payments_enabled": bool(settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET),
        })


class RecoveryKeyView(AuthThrottleMixin, APIView):
    """
    PUT replaces the recovery key (needs the current password proof): the browser wraps the
    unlocked master key with a new recovery key and sends the wrap plus a hash of its proof.
    """
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        user = request.user
        if not user.wrapped_master_key:
            return Response({"error": "This account has no password-protected vault."}, status=status.HTTP_400_BAD_REQUEST)
        if not check_sign_in_secret(user, request.data):
            return Response({"error": "Invalid password."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = RecoveryKeySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.recovery_wrapped_master_key = serializer.validated_data["recovery_wrapped_master_key"]
        user.recovery_auth_hash = serializer.validated_data["recovery_auth_hash"]
        user.recovery_key_confirmed_at = timezone.now()
        user.save(update_fields=["recovery_wrapped_master_key", "recovery_auth_hash", "recovery_key_confirmed_at"])
        AuditLog.objects.create(user=user, action="vault.recovery_key_created", target_type="user", target_id=str(user.id))
        return Response({"success": True, "user": UserSerializer(user).data})


class RecoveryKeyConfirmView(APIView):
    """Marks the recovery key made at sign-up as saved, once the user has confirmed it."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not (user.recovery_auth_hash and user.recovery_wrapped_master_key):
            return Response({"error": "There's no recovery key to confirm."}, status=status.HTTP_400_BAD_REQUEST)
        if not user.recovery_key_confirmed_at:
            user.recovery_key_confirmed_at = timezone.now()
            user.save(update_fields=["recovery_key_confirmed_at"])
            AuditLog.objects.create(user=user, action="vault.recovery_key_confirmed", target_type="user", target_id=str(user.id))
        return Response({"success": True, "user": UserSerializer(user).data})


class PasswordResetRequestView(APIView):
    """Emails a single-use reset link. The response is the same whether or not the account exists."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedIPThrottle, PasswordResetEmailThrottle]
    throttle_scope = "password_reset"

    def post(self, request):
        email = str(request.data.get("email") or "").strip().lower()
        if "@" in email:
            send_password_reset_email(email)
        return Response({"success": True, "message": "If an account exists for that email, we've sent a link to reset the password."})


class PasswordResetTokenMixin:
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedIPThrottle]
    throttle_scope = "password_reset_token"

    def user_or_error(self, data):
        user = user_for_reset_token(str(data.get("uid") or ""), str(data.get("token") or ""))
        if user is None:
            return None, Response(
                {"error": "This reset link has expired or was already used. Ask for a new one.", "code": "RESET_LINK_INVALID"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return user, None


class PasswordResetCheckView(PasswordResetTokenMixin, APIView):
    """Validates a reset link and returns the recovery-wrapped master key for the browser to unwrap."""

    def post(self, request):
        user, error = self.user_or_error(request.data)
        if error:
            return error
        response = Response({
            "email": user.email,
            "has_recovery_key": user.has_recovery_key,
            "recovery_wrapped_master_key": user.recovery_wrapped_master_key if user.has_recovery_key else "",
            "has_vault": bool(user.wrapped_master_key),
        })
        response["Cache-Control"] = "no-store"
        return response


class PasswordResetCompleteView(PasswordResetTokenMixin, APIView):
    def post(self, request):
        user, error = self.user_or_error(request.data)
        if error:
            return error
        serializer = PasswordResetCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=user.pk)
            # Re-checked under the row lock so two submissions can't both use one link.
            if not reset_tokens.check_token(user, str(request.data.get("token") or "")):
                return self.user_or_error({})[1]
            if data["mode"] == "recovery":
                if not recovery_proof_matches(user, data["recovery_auth"]):
                    return Response(
                        {"error": "That recovery key doesn't match this account.", "code": "RECOVERY_KEY_MISMATCH"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                fields = ["wrapped_master_key", "kdf_salt", "kdf_params"]
            else:
                # No recovery key: a new, empty vault. Files encrypted with the old one can't be decrypted.
                user.public_key = data["public_key"]
                user.wrapped_private_key = data["wrapped_private_key"]
                user.recovery_wrapped_master_key = ""
                user.recovery_auth_hash = ""
                user.recovery_key_confirmed_at = None
                fields = ["wrapped_master_key", "kdf_salt", "kdf_params", "public_key", "wrapped_private_key",
                          "recovery_wrapped_master_key", "recovery_auth_hash", "recovery_key_confirmed_at"]
            user.wrapped_master_key = data["wrapped_master_key"]
            user.kdf_salt = data["kdf_salt"]
            user.kdf_params = data["kdf_params"]
            # Changing the password hash also makes this reset link unusable.
            set_auth_key(user, data["auth_key"])
            user.save(update_fields=[*fields, "password", "auth_scheme"])

        revoked = revoke_other_sessions(user)
        clear_failed_auth(user.email)
        AuditLog.objects.create(
            user=user,
            action="user.password_reset" if data["mode"] == "recovery" else "user.password_reset_vault_replaced",
            target_type="user",
            target_id=str(user.id),
            metadata={"sessions_revoked": revoked},
        )
        return Response({"success": True, "message": "Password changed. Sign in with your new password."})
