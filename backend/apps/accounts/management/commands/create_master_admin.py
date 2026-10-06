import os

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.billing.models import Subscription
from apps.storage.models import StorageQuota


def get_master_admin_credentials(options=None):
    """
    Master admin credentials come from the environment (or CLI options), never from source code.
    Returns (email, password); either may be empty when not configured.
    """
    options = options or {}
    email = (options.get("email") or os.environ.get("MASTER_ADMIN_EMAIL", "")).strip().lower()
    password = options.get("password") or os.environ.get("MASTER_ADMIN_PASSWORD", "")
    return email, password


class Command(BaseCommand):
    help = (
        "Create or update the master admin superuser from MASTER_ADMIN_EMAIL / MASTER_ADMIN_PASSWORD "
        "(or --email / --password). Does nothing when they are not configured."
    )

    def add_arguments(self, parser):
        parser.add_argument("--email", default=None, help="Master admin email (overrides MASTER_ADMIN_EMAIL)")
        parser.add_argument("--password", default=None, help="Master admin password (overrides MASTER_ADMIN_PASSWORD)")

    def handle(self, *args, **options):
        email, password = get_master_admin_credentials(options)
        if not email or not password:
            self.stdout.write(
                self.style.WARNING(
                    "MASTER_ADMIN_EMAIL / MASTER_ADMIN_PASSWORD not set; skipping master admin provisioning."
                )
            )
            return
        if len(password) < 12:
            self.stderr.write(self.style.ERROR("MASTER_ADMIN_PASSWORD must be at least 12 characters; skipping."))
            return

        self.stdout.write(f"Creating / updating master admin superuser: {email}...")

        user, created = User.objects.update_or_create(
            email=email,
            defaults={
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
            },
        )
        if created:
            user.full_name = "Master Admin"
            user.email_verified_at = timezone.now()
        user.set_password(password)
        user.save()

        # Super Admin is purely an administrator: NO user pack / subscription is assigned to him,
        # ensuring the entire pool remains available for customers.
        Subscription.objects.filter(user=user).delete()

        quota, _ = StorageQuota.objects.get_or_create(user=user)
        quota.bytes_limit = 0
        quota.bytes_used = 0
        quota.save(update_fields=["bytes_limit", "bytes_used"])

        action_str = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(f"✓ {action_str} master admin superuser {email} (password from environment).")
        )
