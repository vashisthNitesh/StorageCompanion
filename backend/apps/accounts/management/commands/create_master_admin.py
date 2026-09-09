from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import User
from apps.billing.models import Plan, Subscription
from apps.storage.models import StorageQuota


class Command(BaseCommand):
    help = "Create or update the master admin superuser (nitesh-vashisth)"

    def handle(self, *args, **options):
        email = "nitesh-vashisth@smartspacedata.com"
        password = "vashisth@0000"

        self.stdout.write(f"Creating / updating master admin superuser: {email}...")

        user, created = User.objects.update_or_create(
            email=email,
            defaults={
                "full_name": "Nitesh Vashisth (Master Admin)",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "wrapped_master_key": "eyJhbGciOiJYWUVTMjU2IiwiY3BoIjoiYWRtaW5fbWFzdGVyX2tleV9ibG9iIn0=",
                "kdf_salt": "7b8e5d2c1f0a9b8e6d4c2b0a8e1f3d5e",
                "kdf_params": {"m": 65536, "t": 3, "p": 4},
                "public_key": "x25519_pub_admin_abcdef0123456789",
                "wrapped_private_key": "wrapped_priv_admin_1234567890abcdef",
                "recovery_wrapped_master_key": "recovery_blob_admin_0987654321",
                "email_verified_at": timezone.now(),
            },
        )
        user.set_password(password)
        user.save()

        # Super Admin is purely an administrator: NO user pack / subscription is assigned to him,
        # ensuring the entire 1000 GB pool remains untouched and 100% available for users!
        Subscription.objects.filter(user=user).delete()

        quota, _ = StorageQuota.objects.get_or_create(user=user)
        quota.bytes_limit = 0
        quota.bytes_used = 0
        quota.save(update_fields=["bytes_limit", "bytes_used"])

        action_str = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ {action_str} superuser successfully!\n"
                f"  Username/Email: nitesh-vashisth ({email})\n"
                f"  Password: {password}\n"
                f"  Role: Superuser / Master Admin\n"
                f"  Subscription: None (Administrator - zero user pool quota consumed)"
            )
        )
