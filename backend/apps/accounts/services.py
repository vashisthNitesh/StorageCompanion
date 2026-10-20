import io
import base64
import secrets
import json
import hmac
import hashlib
import urllib.error
import urllib.parse
import urllib.request
import uuid
import pyotp
import qrcode
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.core.cache import cache
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed, Throttled
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import User, MFADevice, Session
from apps.audit.models import AuditLog


GOOGLE_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}

# Failed sign-in attempts (wrong password or wrong MFA code) allowed per account
# before further attempts are refused for the lockout window.
MAX_FAILED_AUTH_ATTEMPTS = 8
FAILED_AUTH_WINDOW_SECONDS = 15 * 60


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


# ---------------------------------------------------------------------------
# Brute-force protection
# ---------------------------------------------------------------------------

def _failed_auth_key(identifier: str) -> str:
    digest = hashlib.sha256(identifier.lower().strip().encode("utf-8")).hexdigest()
    return f"auth-failures:{digest}"


def ensure_not_locked_out(identifier: str) -> None:
    if cache.get(_failed_auth_key(identifier), 0) >= MAX_FAILED_AUTH_ATTEMPTS:
        raise Throttled(
            wait=FAILED_AUTH_WINDOW_SECONDS,
            detail="Too many failed sign-in attempts. Please wait 15 minutes and try again.",
        )


def record_failed_auth(identifier: str) -> None:
    key = _failed_auth_key(identifier)
    if not cache.add(key, 1, FAILED_AUTH_WINDOW_SECONDS):
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, FAILED_AUTH_WINDOW_SECONDS)


def clear_failed_auth(identifier: str) -> None:
    cache.delete(_failed_auth_key(identifier))


# ---------------------------------------------------------------------------
# Sessions & tokens
# ---------------------------------------------------------------------------

def issue_session_tokens(user: User, request=None, audit_action: str | None = "auth.login") -> tuple[RefreshToken, Session]:
    """
    Creates a tracked Session and a refresh token bound to it through the "sid" claim.
    Access tokens derived from the refresh token inherit the claim, so revoking the
    session invalidates both immediately.
    """
    session_id = uuid.uuid4()
    refresh = RefreshToken.for_user(user)
    refresh["sid"] = str(session_id)

    ip = get_client_ip(request) if request else None
    ua = request.META.get("HTTP_USER_AGENT", "") if request else ""
    session = Session.objects.create(
        id=session_id,
        user=user,
        token_jti=str(refresh["jti"]),
        device_label=parse_user_agent_label(ua),
        ip_address=ip,
        user_agent=ua,
    )
    if request and audit_action:
        AuditLog.objects.create(
            user=user,
            action=audit_action,
            target_type="user",
            target_id=str(user.id),
            ip=ip,
            user_agent=ua,
            metadata={"session_id": str(session.id)},
        )
    return refresh, session


def rotate_refresh_token(raw_refresh: str) -> tuple[User, RefreshToken]:
    """
    Validates a refresh token, checks its session is still active, blacklists it and
    returns a new refresh token for the same session.
    """
    try:
        token = RefreshToken(raw_refresh)
    except TokenError as e:
        raise AuthenticationFailed(str(e))

    session_id = token.payload.get("sid")
    user_id = token.payload.get(settings.SIMPLE_JWT["USER_ID_CLAIM"])
    session = Session.objects.select_related("user").filter(id=session_id, user_id=user_id).first() if session_id else None
    if session is None or session.revoked_at is not None:
        raise AuthenticationFailed("This session has been signed out.")
    user = session.user
    if not user.is_active:
        raise AuthenticationFailed("This account has been deactivated or suspended.")

    try:
        token.blacklist()
    except TokenError:
        pass

    new_refresh = RefreshToken.for_user(user)
    new_refresh["sid"] = str(session.id)
    session.token_jti = str(new_refresh["jti"])
    session.last_seen = timezone.now()
    session.save(update_fields=["token_jti", "last_seen"])
    return user, new_refresh


def revoke_session(session: Session) -> None:
    """Marks a session revoked and blacklists its current refresh token."""
    if session.revoked_at is None:
        session.revoked_at = timezone.now()
        session.save(update_fields=["revoked_at"])
    outstanding = OutstandingToken.objects.filter(jti=session.token_jti).first()
    if outstanding:
        BlacklistedToken.objects.get_or_create(token=outstanding)


def revoke_other_sessions(user: User, keep_session_id: str | None = None) -> int:
    sessions = Session.objects.filter(user=user, revoked_at__isnull=True)
    if keep_session_id:
        sessions = sessions.exclude(id=keep_session_id)
    count = 0
    for session in sessions:
        revoke_session(session)
        count += 1
    return count


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

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
    from apps.storage.models import StorageQuota
    StorageQuota.objects.get_or_create(user=user)

    refresh, _ = issue_session_tokens(user, request, audit_action="user.registered")
    return user, refresh


def parse_user_agent_label(ua: str) -> str:
    if not ua:
        return "Unknown Device"
    ua_lower = ua.lower()
    os_name = "Desktop"
    if "iphone" in ua_lower or "ipad" in ua_lower:
        os_name = "iOS"
    elif "android" in ua_lower:
        os_name = "Android"
    elif "macintosh" in ua_lower or "mac os" in ua_lower:
        os_name = "macOS"
    elif "windows" in ua_lower:
        os_name = "Windows"
    elif "linux" in ua_lower:
        os_name = "Linux"

    browser_name = "Browser"
    if "edg" in ua_lower:
        browser_name = "Edge"
    elif "chrome" in ua_lower:
        browser_name = "Chrome"
    elif "firefox" in ua_lower:
        browser_name = "Firefox"
    elif "safari" in ua_lower:
        browser_name = "Safari"

    return f"{browser_name} on {os_name}"


# ---------------------------------------------------------------------------
# MFA
# ---------------------------------------------------------------------------

def setup_totp_mfa(user: User, device_name: str = "Authenticator App"):
    secret = pyotp.random_base32()
    # Generate 10 random 8-character backup codes
    raw_backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
    hashed_backup_codes = [make_password(code) for code in raw_backup_codes]

    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(name=user.email, issuer_name="SmartSpace")

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
        code = (code or "").replace(" ", "").strip()
        totp = pyotp.TOTP(device.secret)
        if totp.verify(code, valid_window=1):
            return True

        # Check backup codes
        for idx, hashed in enumerate(device.backup_codes):
            if check_password(code.upper(), hashed):
                # Consume backup code
                device.backup_codes.pop(idx)
                device.save(update_fields=["backup_codes"])
                return True
        return False
    except Exception:
        return False


def check_mfa_for_login(user: User, totp_code: str | None) -> bool:
    """
    Returns True when the user may proceed, False when an MFA code is still needed.
    Wrong codes count towards the account lockout and raise AuthenticationFailed.
    """
    if not user.mfa_enabled:
        return True
    if not totp_code:
        return False
    if not verify_totp_code(user, totp_code):
        record_failed_auth(user.email)
        raise AuthenticationFailed("Invalid two-factor authentication code.")
    return True


# ---------------------------------------------------------------------------
# Google Sign-In
# ---------------------------------------------------------------------------

def verify_google_credential(credential: str) -> dict:
    """
    Verifies a Google Identity Services ID token with Google and checks it was issued
    for this app's client ID by Google for a verified email address.
    """
    if not credential:
        raise AuthenticationFailed("Missing Google credential.")

    google_client_id = getattr(settings, "GOOGLE_CLIENT_ID", "")
    if not google_client_id:
        raise AuthenticationFailed("Google sign-in is not configured on this server.")

    token_url = "https://oauth2.googleapis.com/tokeninfo?" + urllib.parse.urlencode({"id_token": credential})
    try:
        req = urllib.request.Request(token_url, headers={"User-Agent": "SmartSpace-Auth/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError:
        raise AuthenticationFailed("Google sign-in failed: the Google token is invalid or expired.")
    except Exception:
        raise AuthenticationFailed("Could not reach Google to verify your sign-in. Please try again.")

    if payload.get("aud") != google_client_id:
        raise AuthenticationFailed("Google token was not issued for this application.")
    if payload.get("iss") not in GOOGLE_ISSUERS:
        raise AuthenticationFailed("Google token has an invalid issuer.")
    try:
        if int(payload.get("exp", 0)) < int(timezone.now().timestamp()):
            raise AuthenticationFailed("Google token has expired. Please sign in again.")
    except (TypeError, ValueError):
        raise AuthenticationFailed("Google token has an invalid expiry.")
    if not payload.get("email") or not payload.get("sub"):
        raise AuthenticationFailed("Google did not return an email address for this account.")
    if str(payload.get("email_verified", "")).lower() != "true":
        raise AuthenticationFailed("Your Google email address is not verified.")

    return payload


def derive_google_vault_key(user: User, google_sub: str) -> str:
    """Deterministic 32-byte (64 hex char) vault key for accounts created through Google sign-in."""
    message = f"storage_companion:vault:{user.id}:{google_sub}".encode("utf-8")
    secret = getattr(settings, "VAULT_KEY_SECRET", "") or settings.SECRET_KEY
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def resolve_google_user(payload: dict) -> tuple[User, bool]:
    """
    Finds or creates the account for a verified Google identity.
    Returns (user, is_new).
    """
    email = payload["email"].lower().strip()
    google_sub = str(payload["sub"])

    user = User.objects.filter(google_sub=google_sub).first()
    if user is None:
        user = User.objects.filter(email__iexact=email).first()
        if user is not None and user.google_sub and user.google_sub != google_sub:
            raise AuthenticationFailed("This email is linked to a different Google account.")

    is_new = False
    if user is None:
        user = User.objects.create_user(
            email=email,
            full_name=payload.get("name", ""),
            email_verified_at=timezone.now(),
            google_sub=google_sub,
            is_active=True,
        )
        is_new = True
        from apps.storage.models import StorageQuota
        StorageQuota.objects.get_or_create(user=user)
    elif not user.google_sub:
        if user.has_usable_password() and not user.email_verified_at:
            # The address on a password account was never verified by us, so linking it to a
            # Google identity could hand someone else's pre-registered account to this person.
            raise AuthenticationFailed(
                "An account with this email already exists. Sign in with your email and password."
            )
        user.google_sub = google_sub
        if not user.email_verified_at:
            user.email_verified_at = timezone.now()
        user.save(update_fields=["google_sub", "email_verified_at"])

    if not user.is_active:
        raise AuthenticationFailed("This account has been deactivated or suspended.")
    return user, is_new


def google_vault_key_for(user: User) -> str | None:
    """
    Accounts created with Google have a vault key derived on the server. Accounts that
    were created with a password keep their password-protected vault, so no key is
    returned and the browser asks for the vault password instead.
    """
    if user.wrapped_master_key or not user.google_sub:
        return None
    return derive_google_vault_key(user, user.google_sub)
