"""
Sign-in secrets and password reset for the zero-knowledge vault.

The browser derives a key-encryption key (KEK) from the password with Argon2id and, from it,
an auth key (HKDF, info "smartspace-auth-v1"). Only the auth key is sent; the server stores it
with its own password hasher. The password, the master key and the recovery key never reach
the server in a usable form. Staff accounts and accounts created before this scheme send the
password; a customer's next sign-in upgrades the account to the auth key.
"""
import hashlib
import hmac
import logging
import re

from django.conf import settings
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from apps.accounts.models import User

logger = logging.getLogger(__name__)

HEX_256 = re.compile(r"^[0-9a-f]{64}$")
DEFAULT_KDF_PARAMS = {"iterations": 3, "memorySize": 65536, "parallelism": 4, "hashLength": 32}

reset_tokens = PasswordResetTokenGenerator()


def is_hex_256(value) -> bool:
    return isinstance(value, str) and bool(HEX_256.match(value))


def uses_auth_key(user: User) -> bool:
    return user.auth_scheme == User.AUTH_SCHEME_AUTH_KEY


def check_sign_in_secret(user: User, data) -> bool:
    """
    Checks the secret a request proves the account with: the derived auth key for upgraded
    accounts, the password otherwise.
    """
    secret = data.get("auth_key") if uses_auth_key(user) else data.get("password")
    return bool(secret) and isinstance(secret, str) and user.has_usable_password() and user.check_password(secret)


def set_auth_key(user: User, auth_key: str) -> None:
    """Stores a new auth key as the account's sign-in secret (the caller saves the user)."""
    user.set_password(auth_key)
    user.auth_scheme = User.AUTH_SCHEME_AUTH_KEY


def prelogin_params(email: str) -> dict:
    """
    What the browser needs before signing in: how to form the secret and, for vault accounts,
    the KDF salt and parameters. Unknown emails get a stable made-up salt so the response
    doesn't reveal whether an account exists.
    """
    user = User.objects.filter(email=email).first()
    if user is not None and (user.is_staff or user.is_superuser or not user.wrapped_master_key):
        return {"scheme": User.AUTH_SCHEME_PASSWORD, "kdf_salt": "", "kdf_params": {}}
    if user is not None:
        return {"scheme": user.auth_scheme, "kdf_salt": user.kdf_salt, "kdf_params": user.kdf_params or DEFAULT_KDF_PARAMS}
    fake_salt = hmac.new(settings.SECRET_KEY.encode(), f"prelogin-salt:{email}".encode(), hashlib.sha256).hexdigest()[:32]
    return {"scheme": User.AUTH_SCHEME_AUTH_KEY, "kdf_salt": fake_salt, "kdf_params": DEFAULT_KDF_PARAMS}


def recovery_proof_matches(user: User, recovery_auth: str) -> bool:
    if not user.has_recovery_key or not is_hex_256(recovery_auth):
        return False
    digest = hashlib.sha256(bytes.fromhex(recovery_auth)).hexdigest()
    return hmac.compare_digest(digest, user.recovery_auth_hash)


# ---------------------------------------------------------------------------
# Password reset by email (single-use token, PASSWORD_RESET_TIMEOUT seconds)
# ---------------------------------------------------------------------------

def can_reset_password(user: User) -> bool:
    """Customers with a password (or a password vault). Staff passwords are managed by the operator."""
    return user.is_active and not (user.is_staff or user.is_superuser) and (user.has_usable_password() or bool(user.wrapped_master_key))


def site_url() -> str:
    return (settings.PUBLIC_SITE_URL or ("http://localhost:5173" if settings.DEBUG else "https://smartspacedata.com")).rstrip("/")


def reset_link_for(user: User) -> str:
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    # In the fragment, so the token never reaches server logs or Referer headers.
    return f"{site_url()}/reset-password#uid={uid}&token={reset_tokens.make_token(user)}"


def user_for_reset_token(uid: str, token: str) -> User | None:
    try:
        pk = force_str(urlsafe_base64_decode(uid or ""))
        user = User.objects.filter(pk=pk).first()
    except (ValueError, TypeError, OverflowError):
        return None
    if user is None or not can_reset_password(user) or not reset_tokens.check_token(user, token or ""):
        return None
    return user


def send_password_reset_email(email: str) -> None:
    """Sends a reset link if the account can reset its password. Silent otherwise."""
    user = User.objects.filter(email=email).first()
    if user is None or not user.is_active:
        return
    minutes = settings.PASSWORD_RESET_TIMEOUT // 60
    if can_reset_password(user):
        subject = "Reset your SmartSpace password"
        body = (
            "Someone asked to reset the password for your SmartSpace account.\n\n"
            f"Open this link within {minutes} minutes to choose a new password:\n{reset_link_for(user)}\n\n"
            "You'll need your recovery key to keep access to your files.\n\n"
            "If you didn't ask for this, you can ignore this email; your password stays the same."
        )
    elif user.google_sub and not (user.is_staff or user.is_superuser):
        subject = "Signing in to SmartSpace"
        body = (
            "Someone asked to reset the password for your SmartSpace account.\n\n"
            f"Your account uses Google sign-in, so there's no password to reset. Sign in with Google at {site_url()}/login.\n"
        )
    else:
        return
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [user.email])
    except Exception:  # noqa: BLE001 - the response must not reveal delivery problems
        logger.exception("Could not send the password reset email")
