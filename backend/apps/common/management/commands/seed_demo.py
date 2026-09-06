from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import User
from apps.billing.models import Plan, Subscription, Invoice
from apps.storage.models import Node, FileVersion, StorageQuota


class Command(BaseCommand):
    help = "Seed SmartSpace Data 'Paisa Vasool' plans and a realistic demo vault."

    def handle(self, *args, **options):
        self.stdout.write("Seeding SmartSpace Data subscription plans (5 'Paisa Vasool' Tiers)...")

        # 1. Entry Pack (25 GB - ₹39/mo)
        entry_plan, _ = Plan.objects.update_or_create(
            code="entry",
            defaults={
                "name": "Entry Pack",
                "description": "Essential cloud vault for documents, tax receipts, and personal archives.",
                "storage_bytes": 25 * 1024 * 1024 * 1024,  # 25 GB
                "price_monthly": 39.00,
                "price_yearly": 390.00,
                "currency": "INR",
                "max_file_size": 5 * 1024 * 1024 * 1024,  # 5 GB
                "version_retention_days": 15,
                "sort_order": 1,
                "is_active": True,
                "features": [
                    "25 GB Encrypted Storage",
                    "100% Original RAW Quality",
                    "Zero Egress Bandwidth Fees",
                    "Client-Side Zero-Knowledge Encryption",
                    "1-Click UPI via Razorpay",
                ],
            },
        )

        # 2. Smart Pack (100 GB - ₹89/mo)
        smart_plan, _ = Plan.objects.update_or_create(
            code="smart",
            defaults={
                "name": "Smart Pack",
                "description": "Affordable expansion for students, creators, and personal photo libraries.",
                "storage_bytes": 100 * 1024 * 1024 * 1024,  # 100 GB
                "price_monthly": 89.00,
                "price_yearly": 890.00,
                "currency": "INR",
                "max_file_size": 10 * 1024 * 1024 * 1024,  # 10 GB
                "version_retention_days": 30,
                "sort_order": 2,
                "is_active": True,
                "features": [
                    "100 GB Encrypted Storage",
                    "100% Original RAW Quality",
                    "Zero Egress Bandwidth Fees",
                    "Client-Side Decrypted Search",
                    "Password-Protected Share Links",
                ],
            },
        )

        # 3. Value Pack (200 GB - ₹149/mo) - THE HERO FLAGSHIP
        value_plan, _ = Plan.objects.update_or_create(
            code="value",
            defaults={
                "name": "Value Pack",
                "description": "India's #1 'Paisa Vasool' plan. Tailored for freelance wedding photographers, video editors, and indie filmmakers.",
                "storage_bytes": 200 * 1024 * 1024 * 1024,  # 200 GB
                "price_monthly": 149.00,
                "price_yearly": 1490.00,
                "currency": "INR",
                "max_file_size": 20 * 1024 * 1024 * 1024,  # 20 GB
                "version_retention_days": 30,
                "sort_order": 3,
                "is_active": True,
                "features": [
                    "200 GB Uncompressed Storage",
                    "100% Original RAW, 4K & ZIP Quality",
                    "Zero Egress Bandwidth Fees",
                    "Direct Presigned Object Uploads",
                    "30-Day Version Retention",
                    "Instant 1-Click UPI (Paytm, PhonePe, GPay)",
                ],
            },
        )

        # 4. Super Pack (400 GB - ₹249/mo)
        super_plan, _ = Plan.objects.update_or_create(
            code="super",
            defaults={
                "name": "Super Pack",
                "description": "Heavy-duty capacity for active content creators, video production houses, and design studios.",
                "storage_bytes": 400 * 1024 * 1024 * 1024,  # 400 GB
                "price_monthly": 249.00,
                "price_yearly": 2490.00,
                "currency": "INR",
                "max_file_size": 50 * 1024 * 1024 * 1024,  # 50 GB
                "version_retention_days": 60,
                "sort_order": 4,
                "is_active": True,
                "features": [
                    "400 GB Uncompressed Storage",
                    "Unthrottled 4K Video Streaming",
                    "Zero Egress Bandwidth Fees",
                    "X25519 End-to-End Link Sharing",
                    "60-Day Version Retention",
                    "Priority Direct Storage Bandwidth",
                ],
            },
        )

        # 5. Mega Pack (1 TB - ₹449/mo)
        mega_plan, _ = Plan.objects.update_or_create(
            code="mega",
            defaults={
                "name": "Mega Pack",
                "description": "Maximum 1 TB high-performance storage for commercial production agencies and data archives.",
                "storage_bytes": 1000 * 1024 * 1024 * 1024,  # 1,000 GB (1 TB)
                "price_monthly": 449.00,
                "price_yearly": 4490.00,
                "currency": "INR",
                "max_file_size": 100 * 1024 * 1024 * 1024,  # 100 GB
                "version_retention_days": 90,
                "sort_order": 5,
                "is_active": True,
                "features": [
                    "1,000 GB (1 TB) RAW Storage",
                    "100% Uncompressed Multi-Part Archives",
                    "Zero Egress Bandwidth Fees",
                    "Tamper-Proof Audit Logging",
                    "90-Day Version Retention",
                    "Priority 24/7 Dedicated Support",
                ],
            },
        )

        # Keep legacy aliases active to guarantee test backwards compatibility
        Plan.objects.filter(code="personal").update(is_active=False)
        Plan.objects.filter(code="business").update(is_active=False)

        self.stdout.write(
            self.style.SUCCESS(
                "✓ 5 SmartSpace Data Plans Created:\n"
                "  1. Entry Pack:  25 GB @ ₹39 / mo\n"
                "  2. Smart Pack:  100 GB @ ₹89 / mo\n"
                "  3. Value Pack:  200 GB @ ₹149 / mo (Flagship)\n"
                "  4. Super Pack:  400 GB @ ₹249 / mo\n"
                "  5. Mega Pack:   1 TB @ ₹449 / mo"
            )
        )

        # Demo user setup with Value Pack (200 GB)
        demo_email = "demo@smartspacedata.com"
        demo_password = "SmartSpace2026!"
        self.stdout.write(f"Creating demo account: {demo_email} ...")

        demo_user, created = User.objects.update_or_create(
            email=demo_email,
            defaults={
                "full_name": "Aman Sharma (Creator)",
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

        # Also support legacy demo email login if tested
        legacy_user = User.objects.filter(email="demo@speedcloud.local").first()
        if legacy_user:
            legacy_user.set_password(demo_password)
            legacy_user.save()

        # Attach active Value Pack Subscription
        now = timezone.now()
        sub, _ = Subscription.objects.update_or_create(
            user=demo_user,
            defaults={
                "plan": value_plan,
                "provider": "razorpay",
                "provider_subscription_id": "sub_smartspace_seed_001",
                "status": "active",
                "billing_interval": "monthly",
                "current_period_start": now,
                "current_period_end": now + timedelta(days=30),
            },
        )

        Invoice.objects.get_or_create(
            subscription=sub,
            provider_invoice_id="inv_smartspace_001",
            defaults={
                "amount": value_plan.price_monthly,
                "currency": value_plan.currency,
                "status": "paid",
                "issued_at": now,
            },
        )

        # Quota
        quota, _ = StorageQuota.objects.get_or_create(
            user=demo_user,
            defaults={
                "bytes_used": 0,
                "bytes_limit": value_plan.storage_bytes,
            },
        )
        quota.bytes_limit = value_plan.storage_bytes
        quota.save()

        # Seed sample folder hierarchy for creator workflow
        Node.objects.filter(owner=demo_user).delete()

        # Folders
        shoots_folder = Node.objects.create(
            owner=demo_user,
            type=Node.TYPE_FOLDER,
            encrypted_name="RGVsaGlfV2VkZGluZ180S19SQVc=",  # Delhi_Wedding_4K_RAW
            name_nonce="11223344556677889900aabb",
            size_bytes=0,
        )

        client_deliveries = Node.objects.create(
            owner=demo_user,
            type=Node.TYPE_FOLDER,
            encrypted_name="Q2xpZW50X0ZpbmFsX0RlbGl2ZXJpZXM=",  # Client_Final_Deliveries
            name_nonce="22334455667788990011bbcc",
            size_bytes=0,
        )

        portfolio_folder = Node.objects.create(
            owner=demo_user,
            type=Node.TYPE_FOLDER,
            encrypted_name="Q3JlYXRpdmVfUG9ydGZvbGlvX0FyY2hpdmU=",  # Creative_Portfolio_Archive
            name_nonce="33445566778899001122ccdd",
            size_bytes=0,
        )

        # Sample uncompressed RAW / 4K files
        f1_size = 28 * 1024 * 1024  # 28 MB RAW Photo
        f1 = Node.objects.create(
            owner=demo_user,
            parent=shoots_folder,
            type=Node.TYPE_FILE,
            encrypted_name="V2VkZGluZ19DRV9VbmNvbXByZXNzZWRfUkFXLmNyMw==",  # Wedding_CE_Uncompressed_RAW.cr3
            name_nonce="44556677889900112233ddee",
            size_bytes=f1_size,
        )
        FileVersion.objects.create(
            node=f1,
            version_no=1,
            object_key=f"vault/{demo_user.id}/file_wedding_raw.enc",
            size_bytes=f1_size,
            wrapped_file_key="file_key_wrapped_demo_1",
            content_nonce="55667788990011223344eeff",
        )

        f2_size = 120 * 1024 * 1024  # 120 MB 4K Video Teaser
        f2 = Node.objects.create(
            owner=demo_user,
            parent=client_deliveries,
            type=Node.TYPE_FILE,
            encrypted_name="RGVsaGlfTmlnaHRfVGVhc2VyXzRLX01hc3Rlci5tcDQ=",  # Delhi_Night_Teaser_4K_Master.mp4
            name_nonce="66778899001122334455ff00",
            size_bytes=f2_size,
        )
        FileVersion.objects.create(
            node=f2,
            version_no=1,
            object_key=f"vault/{demo_user.id}/file_teaser_4k.enc",
            size_bytes=f2_size,
            wrapped_file_key="file_key_wrapped_demo_2",
            content_nonce="778899001122334455660011",
        )

        f3_size = 8 * 1024 * 1024  # 8 MB Project Archive
        f3 = Node.objects.create(
            owner=demo_user,
            parent=None,
            type=Node.TYPE_FILE,
            encrypted_name="U21hcnRTcGFjZV9PZmZsaW5lX1JlY292ZXJ5X0tleXMudHh0",  # SmartSpace_Offline_Recovery_Keys.txt
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
                f"✓ SmartSpace Data demo ready!\n"
                f"  Email: {demo_email}\n"
                f"  Password: {demo_password}\n"
                f"  Plan: Value Pack (200 GB @ ₹149/mo)\n"
                f"  Seeded folders: Delhi_Wedding_4K_RAW, Client_Final_Deliveries, Creative_Portfolio_Archive"
            )
        )
