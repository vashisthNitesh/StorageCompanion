from django.conf import settings
from django.utils import timezone
from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken

from apps.accounts.models import User, Session
from apps.accounts.serializers import (
    UserSerializer,
    RegisterSerializer,
    LoginSerializer,
    SessionSerializer,
    ChangePasswordSerializer,
    RecoverySerializer,
)
from apps.accounts.services import (
    register_user,
    create_user_session,
    setup_totp_mfa,
    verify_totp_code,
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


class RegisterView(APIView):
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


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        totp_code = serializer.validated_data.get("totp_code")

        # Check MFA
        if user.mfa_enabled:
            if not totp_code:
                return Response(
                    {
                        "success": False,
                        "mfa_required": True,
                        "message": "MFA verification code required.",
                    },
                    status=status.HTTP_200_OK,
                )
            if not verify_totp_code(user, totp_code):
                return Response(
                    {"error": "Invalid MFA verification code."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        refresh, session = create_user_session(user, request)
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

    def post(self, request):
        cookie_name = settings.SIMPLE_JWT["AUTH_COOKIE"]
        refresh_token = request.COOKIES.get(cookie_name) or request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"error": "Refresh token not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            token = RefreshToken(refresh_token)
            new_access_token = str(token.access_token)
            
            # Rotate refresh token if configured
            if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS", True):
                token.blacklist()
                user_id = token.payload.get(settings.SIMPLE_JWT["USER_ID_CLAIM"])
                user = User.objects.get(id=user_id)
                new_refresh = RefreshToken.for_user(user)
                response = Response({"access_token": new_access_token})
                set_refresh_cookie(response, str(new_refresh))
                return response

            return Response({"access_token": new_access_token})
        except TokenError as e:
            response = Response({"error": str(e)}, status=status.HTTP_401_UNAUTHORIZED)
            clear_refresh_cookie(response)
            return response


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        cookie_name = settings.SIMPLE_JWT["AUTH_COOKIE"]
        refresh_token = request.COOKIES.get(cookie_name) or request.data.get("refresh")

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                # Deactivate session
                Session.objects.filter(token_jti=token.payload.get("jti")).update(
                    revoked_at=timezone.now()
                )
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
        user_data = serializer.data

        # Attach active subscription & quota summary
        subscription = getattr(request.user, "subscription", None)
        quota = getattr(request.user, "storage_quota", None)

        user_data["subscription"] = {
            "has_active_subscription": subscription.is_valid if subscription else False,
            "status": subscription.status if subscription else "no_subscription",
            "plan_name": subscription.plan.name if subscription and subscription.plan else None,
            "plan_code": subscription.plan.code if subscription and subscription.plan else None,
        }
        user_data["quota"] = {
            "bytes_used": quota.bytes_used if quota else 0,
            "bytes_limit": quota.bytes_limit if quota else 0,
            "percent_used": quota.percent_used if quota else 0,
        }

        return Response(user_data)


class ChangePasswordView(APIView):
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

        # Update password & re-wrapped master key
        user.set_password(data["new_password"])
        user.wrapped_master_key = data["new_wrapped_master_key"]
        user.kdf_salt = data["new_kdf_salt"]
        user.kdf_params = data["new_kdf_params"]
        user.save()

        AuditLog.objects.create(
            user=user,
            action="user.password_changed",
            target_type="user",
            target_id=str(user.id),
        )

        return Response({"success": True, "message": "Password updated successfully."})


class MFAEnrollView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        device_data = setup_totp_mfa(request.user)
        return Response(device_data)


class MFAVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        code = request.data.get("code")
        if not code:
            return Response({"error": "Verification code is required."}, status=400)

        device = request.user.mfa_devices.filter(confirmed=False).first()
        if not device:
            return Response({"error": "No pending MFA setup found."}, status=400)

        import pyotp
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


class MFADisableView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        password = request.data.get("password")
        if not password or not request.user.check_password(password):
            return Response({"error": "Invalid password."}, status=400)

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

    def get_queryset(self):
        return Session.objects.filter(user=self.request.user)


class SessionRevokeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, session_id):
        session = Session.objects.filter(id=session_id, user=request.user).first()
        if not session:
            return Response({"error": "Session not found."}, status=404)

        session.revoked_at = timezone.now()
        session.save(update_fields=["revoked_at"])

        AuditLog.objects.create(
            user=request.user,
            action="session.revoked",
            target_type="session",
            target_id=str(session.id),
        )
        return Response({"success": True, "message": "Session revoked."})
