from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import MFADevice, Session, User
from apps.audit.models import AuditLog
from apps.billing.models import Invoice, PaymentEvent, Subscription
from apps.sharing.models import Share
from apps.storage.models import FileVersion, Node, StorageQuota, Upload


class Command(BaseCommand):
    help = "Delete all non-superuser accounts, dummy files, subscriptions, and reset the 1 TB storage pool to 100% free."

    def handle(self, *args, **options):
        self.stdout.write("--- Starting System Data Cleanup ---")

        # 1. Ensure master admin superuser is preserved (credentials from environment only)
        from apps.accounts.management.commands.create_master_admin import (
            get_master_admin_credentials,
        )

        admin_email, admin_password = get_master_admin_credentials()
        if not admin_email or not admin_password:
            self.stderr.write(
                self.style.ERROR(
                    "Refusing to run: set MASTER_ADMIN_EMAIL and MASTER_ADMIN_PASSWORD so the admin account is preserved."
                )
            )
            return

        admin_user, _ = User.objects.update_or_create(
            email=admin_email,
            defaults={"is_staff": True, "is_superuser": True, "is_active": True},
        )
        admin_user.set_password(admin_password)
        admin_user.save()
        self.stdout.write(f"✓ Master Admin preserved: {admin_user.email} (superuser)")

        # 2. Delete all non-superuser accounts (cascades linked records)
        non_superusers = User.objects.exclude(id=admin_user.id)
        deleted_users_count = non_superusers.count()
        non_superusers.delete()
        self.stdout.write(f"✓ Deleted {deleted_users_count} non-superuser account(s).")

        # 3. Clear all subscriptions, invoices, payment events
        sub_count = Subscription.objects.all().count()
        Subscription.objects.all().delete()
        inv_count = Invoice.objects.all().count()
        Invoice.objects.all().delete()
        PaymentEvent.objects.all().delete()
        self.stdout.write(f"✓ Cleared {sub_count} subscription(s) and {inv_count} invoice(s).")

        # 4. Clear all dummy nodes, file versions, uploads, and shares
        nodes_count = Node.objects.all().count()
        Node.objects.all().delete()
        FileVersion.objects.all().delete()
        Upload.objects.all().delete()
        Share.objects.all().delete()
        self.stdout.write(f"✓ Cleared {nodes_count} storage vault node(s) and all files.")

        # 5. Clear / Reset Storage Quotas
        StorageQuota.objects.exclude(user=admin_user).delete()
        admin_quota, _ = StorageQuota.objects.get_or_create(user=admin_user)
        admin_quota.bytes_limit = 0
        admin_quota.bytes_used = 0
        admin_quota.save(update_fields=["bytes_limit", "bytes_used"])
        self.stdout.write("✓ Reset storage quotas. Superuser consumes 0 MB.")

        # 6. Clear dummy audit logs and sessions
        AuditLog.objects.all().delete()
        Session.objects.filter(user__is_superuser=False).delete()
        MFADevice.objects.filter(user__is_superuser=False).delete()

        AuditLog.objects.create(
            user=admin_user,
            action="system.purge_dummy_data",
            ip="127.0.0.1",
            metadata={
                "message": "Purged all dummy users and data. System clean for production/operations.",
                "timestamp": timezone.now().isoformat(),
            },
        )
        self.stdout.write("✓ Purged old audit logs & recorded system initialization event.")

        # 7. Recalculate pool statistics
        pool_stats = StorageQuota.get_global_pool_stats()
        self.stdout.write("\n=== Updated SpaceByte Storage Pool Status ===")
        self.stdout.write(f"  Total Capacity:    {pool_stats['total_pool_gb']} GB")
        self.stdout.write(f"  Used Capacity:     {pool_stats['used_gb']} GB ({pool_stats['percent_used']}%)")
        self.stdout.write(f"  Remaining Space:   {pool_stats['remaining_gb']} GB (100% Available)")
        self.stdout.write(f"  Registered Users:  {User.objects.count()} (Master Admin)")
        self.stdout.write(f"  Subscriptions:     {Subscription.objects.count()} (Clean state)")
        self.stdout.write("=============================================\n")
        self.stdout.write(self.style.SUCCESS("✓ System is completely clean and ready for your operations!"))
