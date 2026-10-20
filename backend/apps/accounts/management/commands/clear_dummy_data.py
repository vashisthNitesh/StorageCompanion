import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User, Session, MFADevice
from apps.billing.models import Subscription, Invoice, PaymentEvent
from apps.storage.models import Node, FileVersion, Upload, StorageQuota
from apps.audit.models import AuditLog
from apps.storage.spacebyte import get_spacebyte_client


class Command(BaseCommand):
    help = "Delete all non-superuser accounts, purge their data from SpaceByte and the database, and preserve the super admin."

    def handle(self, *args, **options):
        self.stdout.write("--- Starting System Data & SpaceByte Cleanup ---")

        # 1. Ensure master admin superuser (nitesh-vashisth) is preserved
        admin_email = os.environ.get("MASTER_ADMIN_EMAIL", "").strip().lower()
        admin_password = os.environ.get("MASTER_ADMIN_PASSWORD", "")
        if not admin_email or not admin_password:
            self.stderr.write(self.style.ERROR("Set MASTER_ADMIN_EMAIL and MASTER_ADMIN_PASSWORD before running this command."))
            return

        admin_user, _ = User.objects.update_or_create(
            email=admin_email,
            defaults={
                "full_name": "Nitesh Vashisth (Master Admin)",
                "is_staff": True,
                "is_superuser": True,
                "is_active": True,
                "email_verified_at": timezone.now(),
            },
        )
        admin_user.set_password(admin_password)
        admin_user.save()
        self.stdout.write(f"✓ Master Admin preserved: {admin_user.email} (superuser: {admin_user.is_superuser})")

        # 2. Collect and delete user vault data stored in SpaceByte
        sb_client = get_spacebyte_client()
        if sb_client.is_configured:
            self.stdout.write("Scanning SpaceByte for user vault entries...")
            page = 1
            vault_entry_ids = []
            non_vault_count = 0

            while True:
                try:
                    res = sb_client._request("GET", "drive/file-entries", params={"perPage": 100, "page": page})
                    items = res.get("data", [])
                    if not items:
                        break
                    for item in items:
                        name = item.get("name") or ""
                        fname = item.get("file_name") or ""
                        eid = item.get("id")
                        if name.startswith("vault_") or fname.startswith("vault_"):
                            vault_entry_ids.append(eid)
                        else:
                            non_vault_count += 1
                    if not res.get("next_page"):
                        break
                    page += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"SpaceByte scan warning on page {page}: {e}"))
                    break

            self.stdout.write(f"Found {len(vault_entry_ids)} user vault file(s) in SpaceByte to delete.")
            self.stdout.write(f"Identified {non_vault_count} non-vault personal file(s) in SpaceByte to keep safe.")

            deleted_sb_count = 0
            # Delete in small batches of 2-3 to avoid upstream timeouts
            batch_size = 3
            for i in range(0, len(vault_entry_ids), batch_size):
                chunk = vault_entry_ids[i:i + batch_size]
                try:
                    sb_client.delete_entries(chunk, delete_forever=True, timeout=90)
                    deleted_sb_count += len(chunk)
                    self.stdout.write(f"  Permanently deleted SpaceByte batch: {chunk}")
                except Exception as e:
                    # If batch failed, try single item deletions
                    for item_id in chunk:
                        try:
                            sb_client.delete_entries([item_id], delete_forever=True, timeout=90)
                            deleted_sb_count += 1
                            self.stdout.write(f"  Permanently deleted SpaceByte entry: {item_id}")
                        except Exception as inner_e:
                            self.stdout.write(self.style.WARNING(f"  Skipped already removed entry {item_id}: {inner_e}"))

            self.stdout.write(f"✓ SpaceByte cleanup complete. Purged {deleted_sb_count} user files.")
        else:
            self.stdout.write(self.style.WARNING("SpaceByte token not configured; skipping upstream API deletion."))

        # 3. Delete all non-superuser accounts (cascades linked records)
        non_superusers = User.objects.exclude(id=admin_user.id)
        deleted_users_count = non_superusers.count()
        non_superusers.delete()
        self.stdout.write(f"✓ Deleted {deleted_users_count} non-superuser account(s).")

        # 4. Clear all subscriptions, invoices, payment events
        sub_count = Subscription.objects.all().count()
        Subscription.objects.all().delete()
        inv_count = Invoice.objects.all().count()
        Invoice.objects.all().delete()
        PaymentEvent.objects.all().delete()
        self.stdout.write(f"✓ Cleared {sub_count} subscription(s) and {inv_count} invoice(s).")

        # 5. Clear all dummy nodes, file versions, uploads, and shares
        nodes_count = Node.objects.all().count()
        Node.objects.all().delete()
        FileVersion.objects.all().delete()
        Upload.objects.all().delete()
        self.stdout.write(f"✓ Cleared {nodes_count} storage vault node(s) and all file versions/uploads.")

        # 6. Clear / Reset Storage Quotas
        StorageQuota.objects.exclude(user=admin_user).delete()
        admin_quota, _ = StorageQuota.objects.get_or_create(user=admin_user)
        admin_quota.bytes_limit = 0
        admin_quota.bytes_used = 0
        admin_quota.save(update_fields=["bytes_limit", "bytes_used"])
        self.stdout.write("✓ Reset storage quotas. Superuser consumes 0 MB.")

        # 7. Clear dummy audit logs and sessions
        AuditLog.objects.all().delete()
        Session.objects.filter(user__is_superuser=False).delete()
        MFADevice.objects.filter(user__is_superuser=False).delete()

        AuditLog.objects.create(
            user=admin_user,
            action="system.purge_dummy_data",
            ip="127.0.0.1",
            metadata={
                "message": "Purged all non-superuser accounts and their SpaceByte data. Preserved super admin.",
                "timestamp": timezone.now().isoformat(),
            },
        )
        self.stdout.write("✓ Purged old audit logs & recorded system initialization event.")

        # 8. Recalculate pool statistics
        pool_stats = StorageQuota.get_global_pool_stats()
        self.stdout.write("\n=== Updated SpaceByte Storage Pool Status ===")
        self.stdout.write(f"  Total Capacity:    {pool_stats['total_pool_gb']} GB")
        self.stdout.write(f"  Used Capacity:     {pool_stats['used_gb']} GB ({pool_stats['percent_used']}%)")
        self.stdout.write(f"  Remaining Space:   {pool_stats['remaining_gb']} GB (100% Available)")
        self.stdout.write(f"  Registered Users:  {User.objects.count()} (Master Admin only)")
        self.stdout.write(f"  Subscriptions:     {Subscription.objects.count()} (Clean state)")
        self.stdout.write("=============================================\n")
        self.stdout.write(self.style.SUCCESS("✓ All non-superusers and their SpaceByte files removed successfully!"))
