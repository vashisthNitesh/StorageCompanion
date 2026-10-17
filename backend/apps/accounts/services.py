import io
import base64
import secrets
import json
import hmac
import hashlib
import urllib.request
import pyotp
import qrcode
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import User, MFADevice, Session
from apps.audit.models import AuditLog



def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def register_user(
    email: str,
    password: str,
    wrapped_master_key: str,
    kdf_salt: str,
    kdf_params: dict,
    public_key: str,
    wrapped_private_key: str,
    recovery_wrapped_master_key: str,
    full_name: str = "",
    request=None
) -> tuple[User, RefreshToken]:
    user = User.objects.create_user(
        email=email,
        password=password,
        full_name=full_name,
        wrapped_master_key=wrapped_master_key,
        kdf_salt=kdf_salt,
        kdf_params=kdf_params,
        public_key=public_key,
        wrapped_private_key=wrapped_private_key,
        recovery_wrapped_master_key=recovery_wrapped_master_key,
    )

    refresh = RefreshToken.for_user(user)

    # Track session
    if request:
        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        Session.objects.create(
            user=user,
            token_jti=str(refresh["jti"]),
            device_label=parse_user_agent_label(ua),
            ip_address=ip,
            user_agent=ua,
        )
        AuditLog.objects.create(
            user=user,
            action="user.registered",
            target_type="user",
            target_id=str(user.id),
            ip=ip,
            user_agent=ua,
            metadata={"email": user.email},
        )

    return user, refresh


def create_user_session(user: User, request) -> tuple[RefreshToken, Session]:
    refresh = RefreshToken.for_user(user)
    ip = get_client_ip(request) if request else None
    ua = request.META.get("HTTP_USER_AGENT", "") if request else ""
    session = Session.objects.create(
        user=user,
        token_jti=str(refresh["jti"]),
        device_label=parse_user_agent_label(ua),
        ip_address=ip,
        user_agent=ua,
    )
    if request:
        AuditLog.objects.create(
            user=user,
            action="auth.login",
            target_type="user",
            target_id=str(user.id),
            ip=ip,
            user_agent=ua,
            metadata={"session_id": str(session.id)},
        )
    return refresh, session


def parse_user_agent_label(ua: str) -> str:
    if not ua:
        return "Unknown Device"
    ua_lower = ua.lower()
    os_name = "Desktop"
    if "macintosh" in ua_lower or "mac os" in ua_lower:
        os_name = "macOS"
    elif "windows" in ua_lower:
        os_name = "Windows"
    elif "linux" in ua_lower:
        os_name = "Linux"
    elif "iphone" in ua_lower:
        os_name = "iPhone"
    elif "android" in ua_lower:
        os_name = "Android"

    browser_name = "Browser"
    if "chrome" in ua_lower and "edg" not in ua_lower:
        browser_name = "Chrome"
    elif "firefox" in ua_lower:
        browser_name = "Firefox"
    elif "safari" in ua_lower and "chrome" not in ua_lower:
        browser_name = "Safari"
    elif "edg" in ua_lower:
        browser_name = "Edge"

    return f"{browser_name} on {os_name}"


def setup_totp_mfa(user: User, device_name: str = "Authenticator App"):
    secret = pyotp.random_base32()
    # Generate 10 random 8-character backup codes
    raw_backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
    hashed_backup_codes = [make_password(code) for code in raw_backup_codes]

    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name="SmartSpace Data")

    # Generate QR code image as base64
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Save pending device
    device, _ = MFADevice.objects.update_or_create(
        user=user,
        defaults={
            "secret": secret,
            "backup_codes": hashed_backup_codes,
            "confirmed": False,
            "device_name": device_name,
        },
    )

    return {
        "secret": secret,
        "provisioning_uri": provisioning_uri,
        "qr_code": f"data:image/png;base64,{qr_base64}",
        "backup_codes": raw_backup_codes,
    }


def verify_totp_code(user: User, code: str) -> bool:
    try:
        device = user.mfa_devices.filter(confirmed=True).first()
        if not device:
            return False
        totp = pyotp.TOTP(device.secret)
        if totp.verify(code, valid_window=1):
            return True

        # Check backup codes
        for idx, hashed in enumerate(device.backup_codes):
            if check_password(code, hashed):
                # Consume backup code
                device.backup_codes.pop(idx)
                device.save()
                return True
        return False
    except Exception:
        return False


def verify_google_credential(credential: str) -> dict:
    if not credential:
        raise AuthenticationFailed("Missing Google credential.")

    # Support development / testing mock tokens
    if (getattr(settings, "DEBUG", False) or getattr(settings, "ENVIRONMENT", "") != "production") and credential.startswith("mock_token_"):
        parts = credential.split("_")
        email = f"{parts[2]}@example.com" if len(parts) > 2 else "mockuser@example.com"
        return {
            "sub": f"mock_sub_{email}",
            "email": email,
            "name": "Mock User",
            "email_verified": True,
        }


    token_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={credential}"
    try:
        req = urllib.request.Request(token_url, headers={"User-Agent": "StorageCompanion-Auth/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status != 200:
                raise AuthenticationFailed("Google token verification failed.")
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        raise AuthenticationFailed(f"Failed to verify Google token: {str(e)}")

    if "email" not in payload or "sub" not in payload:
        raise AuthenticationFailed("Invalid token payload returned by Google.")

    # Check aud against GOOGLE_CLIENT_ID if configured
    google_client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
    if google_client_id and payload.get("aud") != google_client_id:
        raise AuthenticationFailed("Google token audience mismatch.")

    return payload


def get_or_create_google_user(payload: dict, request=None) -> tuple[User, RefreshToken, str]:
    email = payload["email"].lower().strip()
    full_name = payload.get("name", "")
    google_sub = str(payload["sub"])

    user = User.objects.filter(email=email).first()
    is_new = False
    if not user:
        user = User.objects.create_user(
            email=email,
            full_name=full_name,
            email_verified_at=timezone.now(),
            is_active=True,
        )
        is_new = True
        # Ensure StorageQuota is initialized
        from apps.storage.models import StorageQuota
        StorageQuota.objects.get_or_create(user=user)

    if not user.is_active:
        raise AuthenticationFailed("This account has been deactivated or suspended.")

    refresh = RefreshToken.for_user(user)

    # Deterministic 32-byte (64 hex char) vault key derived from SECRET_KEY + user id + google sub
    message = f"storage_companion:vault:{user.id}:{google_sub}".encode("utf-8")
    oauth_vault_hex = hmac.new(settings.SECRET_KEY.encode("utf-8"), message, hashlib.sha256).hexdigest()

    # Session and audit tracking
    if request:
        ip = get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        Session.objects.create(
            user=user,
            token_jti=str(refresh["jti"]),
            device_label=parse_user_agent_label(ua),
            ip_address=ip,
            user_agent=ua,
        )
        AuditLog.objects.create(
            user=user,
            action="auth.google_login" if not is_new else "user.registered_google",
            target_type="user",
            target_id=str(user.id),
            ip=ip,
            user_agent=ua,
            metadata={"email": user.email, "google_sub": google_sub},
        )

    return user, refresh, oauth_vault_hex

