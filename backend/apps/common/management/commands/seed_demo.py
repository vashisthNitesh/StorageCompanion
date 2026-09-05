from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import User
from apps.billing.models import Plan, Subscription, Invoice
from apps.storage.models import Node, FileVersion, StorageQuota


class Command(BaseCommand):
    help = "Seed subscription plans and a demo user with a realistic encrypted file tree."

    def handle(self, *args, **options):
        self.stdout.write("Seeding subscription plans (No Free Tier)...")

        personal_plan, _ = Plan.objects.update_or_create(
            code="personal",
            defaults={
                "name": "Personal Plan",
                "description": "Ideal for professionals, creators, and individuals needing secure, private storage.",
                "storage_bytes": 200 * 1024 * 1024 * 1024,  # 200 GB
                "price_monthly": 199.00,
                "price_yearly": 1999.00,
                "currency": "INR",
                "max_file_size": 10 * 1024 * 1024 * 1024,  # 10 GB
                "version_retention_days": 30,
                "sort_order": 1,
                "is_active": True,
                "features": [
                    "200 GB Secure Storage",
                    "Zero-Knowledge Client Encryption",
                    "Blazing Fast Uploads (Direct R2)",
                    "Password Protected Links & Expiry",
                    "Version History (30 Days)",
                    "Up to 5 Synchronized Devices",
                ],
            },
        )

        business_plan, _ = Plan.objects.update_or_create(
            code="business",
            defaults={
                "name": "Business Plan",
                "description": "For high-performance teams, power users, and businesses requiring heavy storage and compliance.",
                "storage_bytes": 2 * 1024 * 1024 * 1024 * 1024,  # 2 TB
                "price_monthly": 499.00,
                "price_yearly": 4999.00,
                "currency": "INR",
                "max_file_size": 50 * 1024 * 1024 * 1024,  # 50 GB
                "version_retention_days": 365,
                "sort_order": 2,
                "is_active": True,
                "features": [
                    "2 TB High-Performance Storage",
                    "Team Access & X25519 Secure Sharing",
                    "Priority Direct-to-R2 Bandwidth",
                    "Unlimited Connected Devices",
                    "Extended 1-Year Version Retention",
                    "Security Audit Logs & Compliance",
                    "Dedicated 24/7 Priority Support",
                ],
            },
        )

        self.stdout.write(self.style.SUCCESS("✓ Plans created: Personal (₹199/mo) and Business (₹499/mo)"))

        # Demo user
        demo_email = "demo@speedcloud.local"
        demo_password = "SpeedCloud2026!"
        self.stdout.write(f"Creating demo account: {demo_email} ...")

        demo_user, created = User.objects.update_or_create(
            email=demo_email,
            defaults={
                "full_name": "Rajesh Kumar",
                "wrapped_master_key": "eyJhbGciOiJYWUVTMjU2IiwiY3BoIjoiZGVtb19tYXN0ZXJfa2V5X2Jsb2IifQ==",
                "kdf_salt": "6a9f4c3b2e1d0f8a7c5e3b1a9f0d2c4e",
                "kdf_params": {"m": 65536, "t": 3, "p": 4},
                "public_key": "x25519_pub_demo_9876543210abcdef",
                "wrapped_private_key": "wrapped_priv_demo_abcdef0123456789",
                "recovery_wrapped_master_key": "recovery_blob_demo_1234567890",
                "email_verified_at": timezone.now(),
                "is_active": True,
            },
        )
        demo_user.set_password(demo_password)
        demo_user.save()

        # Attach active Personal Subscription
        now = timezone.now()
        sub, _ = Subscription.objects.update_or_create(
            user=demo_user,
            defaults={
                "plan": personal_plan,
                "provider": "razorpay",
                "provider_subscription_id": "sub_demo_seed_001",
                "status": "active",
                "billing_interval": "monthly",
                "current_period_start": now,
                "current_period_end": now + timedelta(days=30),
            },
        )

        Invoice.objects.get_or_create(
            subscription=sub,
            provider_invoice_id="inv_demo_001",
            defaults={
                "amount": personal_plan.price_monthly,
                "currency": personal_plan.currency,
                "status": "paid",
                "issued_at": now,
            },
        )

        # Quota
        quota, _ = StorageQuota.objects.get_or_create(
            user=demo_user,
            defaults={
                "bytes_used": 0,
                "bytes_limit": personal_plan.storage_bytes,
            },
        )
        quota.bytes_limit = personal_plan.storage_bytes
        quota.save()

        # Seed sample folder hierarchy
        # Clear existing nodes for clean demo
        Node.objects.filter(owner=demo_user).delete()

        # Folders
        docs_folder = Node.objects.create(
            owner=demo_user,
            type=Node.TYPE_FOLDER,
            encrypted_name="QnVzaW5lc3MgRG9jdW1lbnRz",  # Business Documents
            name_nonce="11223344556677889900aabb",
            size_bytes=0,
        )

        photos_folder = Node.objects.create(
            owner=demo_user,
            type=Node.TYPE_FOLDER,
            encrypted_name="RmFtaWx5IFBob3RvcyAmIE1lbW9yaWVz",  # Family Photos & Memories
            name_nonce="22334455667788990011bbcc",
            size_bytes=0,
        )

        backups_folder = Node.objects.create(
            owner=demo_user,
            type=Node.TYPE_FOLDER,
            encrypted_name="U2VjdXJlIEJhY2t1cHMgKDIwMjYp",  # Secure Backups (2026)
            name_nonce="33445566778899001122ccdd",
            size_bytes=0,
        )

        # Files in docs_folder
        f1_size = 14 * 1024 * 1024  # 14 MB
        f1 = Node.objects.create(
            owner=demo_user,
            parent=docs_folder,
            type=Node.TYPE_FILE,
            encrypted_name="QW5udWFsX0ZpbmFuY2lhbF9SZXBvcnRfMjAyNi5wZGY=",  # Annual_Financial_Report_2026.pdf
            name_nonce="44556677889900112233ddee",
            size_bytes=f1_size,
        )
        FileVersion.objects.create(
            node=f1,
            version_no=1,
            object_key=f"vault/{demo_user.id}/file_financial_report.enc",
            size_bytes=f1_size,
            wrapped_file_key="file_key_wrapped_demo_1",
            content_nonce="55667788990011223344eeff",
        )

        f2_size = 85 * 1024 * 1024  # 85 MB
        f2 = Node.objects.create(
            owner=demo_user,
            parent=photos_folder,
            type=Node.TYPE_FILE,
            encrypted_name="S2VyYWxhX1ZhY2F0aW9uXzRLX01lbW9yaWVzLm1wNA==",  # Kerala_Vacation_4K_Memories.mp4
            name_nonce="66778899001122334455ff00",
            size_bytes=f2_size,
        )
        FileVersion.objects.create(
            node=f2,
            version_no=1,
            object_key=f"vault/{demo_user.id}/file_vacation_video.enc",
            size_bytes=f2_size,
            wrapped_file_key="file_key_wrapped_demo_2",
            content_nonce="778899001122334455660011",
        )

        f3_size = 4 * 1024 * 1024  # 4 MB
        f3 = Node.objects.create(
            owner=demo_user,
            parent=None,  # In root
            type=Node.TYPE_FILE,
            encrypted_name="Q2xvdWRWYXVsdF9SZWNvdmVyeV9LZXlzX1NhZmUudHh0",  # CloudVault_Recovery_Keys_Safe.txt
            name_nonce="889900112233445566771122",
            size_bytes=f3_size,
        )
        FileVersion.objects.create(
            node=f3,
            version_no=1,
            object_key=f"vault/{demo_user.id}/file_recovery_keys.enc",
            size_bytes=f3_size,
            wrapped_file_key="file_key_wrapped_demo_3",
            content_nonce="990011223344556677882233",
        )

        total_bytes = f1_size + f2_size + f3_size
        quota.bytes_used = total_bytes
        quota.save(update_fields=["bytes_used"])

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Demo account ready! Email: {demo_email} | Password: {demo_password}\n"
                f"✓ Seeded 3 folders, 3 encrypted files, and {total_bytes / (1024*1024):.1f} MB used quota."
            )
        )
