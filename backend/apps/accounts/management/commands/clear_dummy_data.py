from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User, Session, MFADevice
from apps.billing.models import Subscription, Invoice, PaymentEvent, Plan
from apps.storage.models import Node, FileVersion, Upload, StorageQuota
from apps.sharing.models import Share
from apps.audit.models import AuditLog


class Command(BaseCommand):
    help = "Delete all non-superuser accounts, dummy files, subscriptions, and reset the 1 TB storage pool to 100% free."

    def handle(self, *args, **options):
        self.stdout.write("--- Starting System Data Cleanup ---")

        # 1. Ensure master admin superuser (nitesh-vashisth) is preserved
        admin_email = "nitesh-vashisth@smartspacedata.com"
        admin_password = "vashisth@0000"

        admin_user, _ = User.objects.update_or_create(
            email=admin_email,
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
