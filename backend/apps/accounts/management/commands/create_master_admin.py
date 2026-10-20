import os

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User
from apps.billing.models import Subscription
from apps.storage.models import StorageQuota


class Command(BaseCommand):
    help = (
        "Create or update the master admin superuser from the MASTER_ADMIN_EMAIL and "
        "MASTER_ADMIN_PASSWORD environment variables. Does nothing if they are not set."
    )

    def handle(self, *args, **options):
        email = os.environ.get("MASTER_ADMIN_EMAIL", "").strip().lower()
        password = os.environ.get("MASTER_ADMIN_PASSWORD", "")

        if not email or not password:
            self.stdout.write("MASTER_ADMIN_EMAIL / MASTER_ADMIN_PASSWORD not set; skipping master admin setup.")
            return
        if len(password) < 12:
            self.stderr.write(self.style.ERROR("MASTER_ADMIN_PASSWORD must be at least 12 characters; skipping."))
            return

        user, created = User.objects.update_or_create(
            email=email,
            defaults={
                "full_name": os.environ.get("MASTER_ADMIN_NAME", "Master Admin"),
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "email_verified_at": timezone.now(),
            },
        )
        if created or not user.check_password(password):
            user.set_password(password)
            user.save()

        # The administrator has no storage plan, so the whole pool stays available for customers.
        Subscription.objects.filter(user=user).delete()
        quota, _ = StorageQuota.objects.get_or_create(user=user)
        quota.bytes_limit = 0
        quota.bytes_used = 0
        quota.save(update_fields=["bytes_limit", "bytes_used"])

        action_str = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"✓ {action_str} master admin {email}"))
